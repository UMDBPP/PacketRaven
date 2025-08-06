use chrono::Timelike;

lazy_static::lazy_static! {
    static ref MINIMUM_ACCESS_INTERVAL: chrono::Duration = chrono::Duration::seconds(10);
}

#[derive(serde::Deserialize, Debug, PartialEq, Clone, serde::Serialize)]
pub struct AprsFiQuery {
    pub api_key: String,
    pub callsigns: Option<Vec<String>>,
    #[serde(skip)]
    last_access: Option<chrono::DateTime<chrono::Local>>,
}

impl AprsFiQuery {
    pub fn new(api_key: String, callsigns: Option<&Vec<String>>) -> Self {
        Self {
            api_key,
            callsigns: callsigns.map(|callsigns| callsigns.to_owned()),
            last_access: None,
        }
    }
}

impl AprsFiQuery {
    fn parameters(&self) -> Result<Vec<(&str, String)>, super::ConnectionError> {
        if let Some(callsigns) = &self.callsigns {
            let parameters = vec![
                ("name", callsigns.join(",")),
                ("what", "loc".to_string()),
                ("apikey", self.api_key.to_owned()),
                ("format", "json".to_string()),
            ];
            Ok(parameters)
        } else {
            Err(super::ConnectionError::FailedToEstablish {
                connection: "APRS.fi".to_string(),
                message: "the API requires a list of callsigns".to_string(),
            })
        }
    }

    pub fn retrieve_aprs_from_aprsfi(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let now = chrono::Local::now();
        if let Some(last_access_time) = self.last_access {
            if now - last_access_time < *MINIMUM_ACCESS_INTERVAL {
                return Err(crate::connection::ConnectionError::TooFrequent {
                    connection: "APRS.fi".to_string(),
                    duration: crate::utilities::duration_string(&MINIMUM_ACCESS_INTERVAL),
                });
            }
        }

        let client = reqwest::blocking::Client::builder()
            .user_agent(crate::connection::USER_AGENT.to_owned())
            .timeout(Some(std::time::Duration::from_secs(10)))
            .build()
            .unwrap();

        let parameters = self.parameters()?;
        let response = client
            .get("https://api.aprs.fi/api/get")
            .query(&parameters)
            .send()
            .unwrap_or_else(|_| panic!("{parameters:?}"));
        let url = response.url().to_string();

        self.last_access = Some(now);

        match response.status() {
            reqwest::StatusCode::OK => {
                // deserialize JSON into struct
                let aprs_fi_response: AprsFiResponse = match response.json() {
                    Ok(object) => object,
                    Err(error) => {
                        return Err(crate::connection::ConnectionError::ApiError {
                            message: error.to_string(),
                            url,
                        })
                    }
                };
                match aprs_fi_response {
                    AprsFiResponse::Ok { entries, .. } => {
                        let mut balloon_locations: Vec<crate::location::BalloonLocation> = vec![];
                        if let AprsFiEntries::Loc(locations) = entries {
                            for location in locations {
                                balloon_locations.push(location.to_balloon_location());
                            }
                        }
                        Ok(balloon_locations)
                    }
                    AprsFiResponse::Fail { description, .. } => {
                        Err(crate::connection::ConnectionError::ApiError {
                            message: description,
                            url,
                        })
                    }
                }
            }
            other => Err(crate::connection::ConnectionError::ApiError {
                message: other.to_string(),
                url,
            }),
        }
    }
}

// https://aprs.fi/page/api
#[derive(serde::Deserialize)]
#[serde(rename_all = "lowercase")]
#[serde(tag = "result")]
enum AprsFiResponse {
    Ok {
        command: String,
        what: String,
        found: u32,
        entries: AprsFiEntries,
    },
    Fail {
        command: String,
        description: String,
    },
}

#[derive(serde::Deserialize)]
#[serde(untagged)]
#[serde(rename_all = "snake_case")]
enum AprsFiEntries {
    Loc(Vec<AprsFiLocation>),
    Wx(Vec<AprsFiWeather>),
    Msg(Vec<AprsFiMessage>),
}

#[derive(serde::Deserialize)]
#[serde(tag = "class")]
#[serde(rename_all = "lowercase")]
enum AprsFiLocation {
    A {
        #[serde(flatten)]
        location: AprsFiLocationRecord,
    },
    I {
        #[serde(flatten)]
        location: AprsFiLocationRecord,
        #[serde(flatten)]
        ais: crate::location::ais::AisData,
    },
    W {
        #[serde(flatten)]
        location: AprsFiLocationRecord,
    },
}

impl AprsFiLocation {
    pub fn to_balloon_location(&self) -> crate::location::BalloonLocation {
        match self {
            Self::A { location } | Self::W { location } => location.to_balloon_location(),
            Self::I { location, ais } => {
                let mut output = location.to_balloon_location();
                output.data.ais = Some(ais.to_owned());
                output
            }
        }
    }
}

#[serde_with::serde_as]
#[derive(serde::Deserialize)]
struct AprsFiLocationRecord {
    name: Option<String>,
    showname: Option<String>,
    #[serde(rename = "type")]
    _type: String,
    #[serde(with = "crate::utilities::utc_timestamp_string")]
    time: chrono::DateTime<chrono::Utc>,
    #[serde(with = "crate::utilities::utc_timestamp_string")]
    lasttime: chrono::DateTime<chrono::Utc>,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    lat: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    lng: f64,
    #[serde(default)]
    #[serde(with = "crate::utilities::optional_f64_string")]
    altitude: Option<f64>,
    #[serde(default)]
    #[serde(with = "crate::utilities::optional_u64_string")]
    course: Option<u64>,
    #[serde(default)]
    #[serde(with = "crate::utilities::optional_f64_string")]
    speed: Option<f64>,
    symbol: Option<String>,
    srccall: String,
    dstcall: String,
    comment: String,
    path: Option<String>,
    phg: Option<String>,
    status: Option<String>,
    status_lasttime: Option<String>,
}

impl AprsFiLocationRecord {
    pub fn to_balloon_location(&self) -> crate::location::BalloonLocation {
        let from = aprs_parser::Callsign::new(&self.srccall).unwrap();

        let mut via = vec![];
        for step in self.path.as_ref().unwrap().split(',') {
            via.push(aprs_parser::Via::decode_textual(step.as_bytes()).unwrap());
        }

        let to = aprs_parser::Callsign::new(&self.dstcall).unwrap();

        let time = self.time.to_owned();

        let symbol_chars: Vec<char> = self.symbol.as_ref().unwrap().chars().collect();

        let aprs_packet = aprs_parser::AprsPacket {
            from,
            via,
            data: aprs_parser::AprsData::Position(aprs_parser::AprsPosition {
                to,
                timestamp: Some(aprs_parser::Timestamp::HHMMSS(
                    time.hour() as u8,
                    time.minute() as u8,
                    time.second() as u8,
                )),
                messaging_supported: false,
                latitude: aprs_parser::Latitude::new(self.lat).unwrap(),
                longitude: aprs_parser::Longitude::new(self.lng).unwrap(),
                precision: aprs_parser::Precision::HundredthMinute,
                symbol_table: symbol_chars[0],
                symbol_code: symbol_chars[1],
                comment: self.comment.to_owned().into_bytes(),
                cst: aprs_parser::AprsCst::Uncompressed,
            }),
        };

        crate::location::BalloonLocation {
            location: crate::location::Location {
                time: time.with_timezone(&chrono::Local),
                coord: geo::coord! { x: self.lng, y: self.lat },
                altitude: self.altitude,
            },
            data: crate::location::BalloonData::new(
                None,
                Some(aprs_packet),
                None,
                None,
                crate::location::LocationSource::AprsFi,
            ),
        }
    }
}

#[derive(serde::Deserialize)]
#[serde(rename_all = "lowercase")]
enum AprsFiTargetType {
    A,
    L,
    I,
    O,
    W,
}

#[serde_with::serde_as]
#[derive(serde::Deserialize)]
struct AprsFiWeather {
    name: String,
    #[serde(with = "crate::utilities::utc_timestamp_string")]
    time: chrono::DateTime<chrono::Utc>,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    temp: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    pressure: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    humidity: u8,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    wind_direction: u8,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    wind_speed: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    wind_gust: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    rain_1h: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    rain_24h: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    rain_mn: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    luminosity: f64,
}

#[serde_with::serde_as]
#[derive(serde::Deserialize)]
struct AprsFiMessage {
    messageid: String,
    time: chrono::DateTime<chrono::Utc>,
    srccall: String,
    dst: String,
    message: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore]
    fn test_api() {
        if let Ok(api_key) = std::env::var("APRS_FI_API_KEY") {
            let callsigns = vec![
                String::from("W3EAX-10"),
                String::from("W3EAX-11"),
                String::from("W3EAX-13"),
                String::from("W3EAX-14"),
            ];

            let mut connection = AprsFiQuery::new(api_key, Some(&callsigns));
            let packets = connection.retrieve_aprs_from_aprsfi().unwrap();

            assert!(!packets.is_empty());
        } else {
            panic!("APRS.fi credentials not set in environment variable");
        }
    }

    #[test]
    fn test_location() {
        let data = r#"
        {
          "class": "a",
          "name": "W3EAX-11",
          "type": "l",
          "time": "1659286185",
          "lasttime": "1659286185",
          "lat": "39.41750",
          "lng": "-77.06550",
          "altitude": "1870.86",
          "course": "146",
          "speed": "13",
          "symbol": "/O",
          "srccall": "W3EAX-11",
          "dstcall": "CQ",
          "comment": ",StrTrk,255,9,1.55V,3C,82725Pa,",
          "path": "N3TJJ-11*,WIDE1*,W3EPE-3*,KB3EJM-11*,WIDE2*,qAR,NA7L"
        }
        "#;
        let response: AprsFiLocation = serde_json::from_str(data).unwrap();

        match response {
            AprsFiLocation::A { location } => {
                assert_eq!(location.srccall, "W3EAX-11");
            }
            _ => panic!(),
        }
    }

    #[test]
    fn test_aprs() {
        let data = r#"
        {
          "command": "get",
          "result": "ok",
          "what": "loc",
          "found": 1,
          "entries": [
            {
              "class": "a",
              "name": "W3EAX-11",
              "type": "l",
              "time": "1659286185",
              "lasttime": "1659286185",
              "lat": "39.41750",
              "lng": "-77.06550",
              "altitude": "1870.86",
              "course": "146",
              "speed": "13",
              "symbol": "/O",
              "srccall": "W3EAX-11",
              "dstcall": "CQ",
              "comment": ",StrTrk,255,9,1.55V,3C,82725Pa,",
              "path": "N3TJJ-11*,WIDE1*,W3EPE-3*,KB3EJM-11*,WIDE2*,qAR,NA7L"
            }
          ]
        }
        "#;
        let response: AprsFiResponse = serde_json::from_str(data).unwrap();

        match response {
            AprsFiResponse::Ok { command, .. } => {
                assert_eq!(command, "get");
            }
            _ => panic!(),
        }
    }

    #[test]
    fn test_aprs_location_string() {
        let data = r#"
        {
          "class": "a",
          "name": "W3EAX-11",
          "type": "l",
          "time": "1659286185",
          "lasttime": "1659286185",
          "lat": "39.41750",
          "lng": "-77.06550",
          "altitude": "1870.86",
          "course": "146",
          "speed": "13",
          "symbol": "/O",
          "srccall": "W3EAX-11",
          "dstcall": "CQ",
          "comment": ",StrTrk,255,9,1.55V,3C,82725Pa,",
          "path": "N3TJJ-11*,WIDE1*,W3EPE-3*,KB3EJM-11*,WIDE2*,qAR,NA7L"
        }
        "#;
        let response: AprsFiLocation = serde_json::from_str(data).unwrap();

        match response {
            AprsFiLocation::A { location } => {
                assert_eq!(location.altitude, Some(1870.86));
            }
            _ => panic!(),
        }
    }

    #[test]
    fn test_aprs_location_number() {
        let data = r#"
        {
          "class": "a",
          "name": "WB4ELK-7",
          "type": "l",
          "time": "1683259848",
          "lasttime": "1684447839",
          "lat": "-52.06250",
          "lng": "142.45817",
          "altitude": 0,
          "course": 90,
          "speed": 0,
          "symbol": "/O",
          "srccall": "WB4ELK-7",
          "dstcall": "",
          "comment": "GPS:0 3.70V -2C 0m QD17FW *083QIY JO40 3* 0kt WB4VHF https://www.ashballoon.info/ 2036",
          "path": "TCPIP*,qAS,WB8MSJ"
        }
        "#;
        let response: AprsFiLocation = serde_json::from_str(data).unwrap();

        match response {
            AprsFiLocation::A { location } => {
                assert_eq!(location.altitude, Some(0.0));
            }
            _ => panic!(),
        }
    }

    #[test]
    fn test_ais() {
        let data = r#"
        {
          "command": "get",
          "result": "ok",
          "what": "loc",
          "found": 1,
          "entries": [
            {
              "class": "i",
              "mmsi": "21BWI",
              "type": "a",
              "time": "1655625488",
              "lasttime": "1682813817",
              "lat": "62.95833",
              "lng": "17.83333",
              "srccall": "21BWI",
              "dstcall": "ais",
              "comment": "JS8 27,246334MHz -19dB"
            }
          ]
        }
        "#;
        let response: AprsFiResponse = serde_json::from_str(data).unwrap();

        match response {
            AprsFiResponse::Ok { command, .. } => {
                assert_eq!(command, "get");
            }
            _ => panic!(),
        }
    }

    #[test]
    fn test_ais_entry() {
        let data = r#"
        {
          "class": "i",
          "mmsi": "21BWI",
          "type": "a",
          "time": "1655625488",
          "lasttime": "1682813817",
          "lat": "62.95833",
          "lng": "17.83333",
          "srccall": "21BWI",
          "dstcall": "ais",
          "comment": "JS8 27,246334MHz -19dB"
        }
        "#;
        let response: AprsFiLocation = serde_json::from_str(data).unwrap();

        match response {
            AprsFiLocation::I { ais, .. } => {
                assert_eq!(ais.mmsi, "21BWI");
            }
            _ => panic!(),
        }
    }

    #[test]
    #[ignore]
    fn test_api_wrong_key() {
        let api_key = String::from("123456.abcdefghijklmno");
        let callsigns = vec![
            String::from("W3EAX-10"),
            String::from("W3EAX-11"),
            String::from("W3EAX-13"),
            String::from("W3EAX-14"),
        ];

        let mut connection = AprsFiQuery::new(api_key, Some(&callsigns));
        assert!(connection.retrieve_aprs_from_aprsfi().is_err());
    }
}
