use chrono::Timelike;

#[derive(serde::Deserialize, Debug)]
pub struct AprsFiQuery {
    pub callsigns: Vec<String>,
    pub api_key: String,
    #[serde(skip)]
    pub timerange: Option<chrono::Duration>,
    #[serde(skip)]
    pub tail: Option<chrono::Duration>,
    #[serde(skip)]
    last_access: Option<chrono::DateTime<chrono::Local>>,
}

impl AprsFiQuery {
    pub fn new(
        callsigns: Vec<String>,
        api_key: String,
        timerange: Option<chrono::Duration>,
        tail: Option<chrono::Duration>,
    ) -> Self {
        Self {
            callsigns,
            api_key,
            timerange,
            tail,
            last_access: None,
        }
    }
}

impl AprsFiQuery {
    fn url(&self) -> String {
        let parameters = vec![
            format!("name={:}", self.callsigns.join(",")),
            format!("what={:}", "loc"),
            format!("apikey={:}", self.api_key),
            format!("format={:}", "json"),
            format!(
                "timerange={:}",
                match self.timerange {
                    Some(duration) => duration,
                    None => chrono::Duration::days(1),
                }
                .num_seconds()
            ),
            format!(
                "tail={:}",
                match self.tail {
                    Some(duration) => duration,
                    None => chrono::Duration::days(1),
                }
                .num_seconds()
            ),
        ];
        format!("https://api.aprs.fi/api/get?{:}", parameters.join("&"))
    }

    pub fn retrieve_aprs_from_aprsfi(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::Error> {
        let now = chrono::Local::now();
        if let Some(last_access_time) = self.last_access {
            if now - last_access_time < chrono::Duration::seconds(10) {
                return Err(crate::connection::Error::TooFrequent);
            }
        }

        let url = self.url();
        let response = reqwest::blocking::get(url).expect("error retrieving packets from APRS.fi");

        self.last_access = Some(now);

        match response.status() {
            reqwest::StatusCode::OK => {
                // deserialize JSON into struct
                let aprs_fi_response: AprsFiResponse = match response.json() {
                    Ok(object) => object,
                    Err(error) => panic!("{:?}", error),
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
                        Err(crate::connection::Error::ApiError {
                            message: description,
                        })
                    }
                }
            }
            _ => Err(crate::connection::Error::ApiError {
                message: String::from("error posting request to API"),
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
        ais: AisData,
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
    #[serde(with = "crate::parse::deserialize_utc_timestamp_string")]
    time: chrono::DateTime<chrono::Utc>,
    #[serde(with = "crate::parse::deserialize_utc_timestamp_string")]
    lasttime: chrono::DateTime<chrono::Utc>,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    lat: f64,
    #[serde_as(as = "serde_with::DisplayFromStr")]
    lng: f64,
    // TODO `serde_as` does not currently support deserializing a `FromStr` in an `Option`
    altitude: Option<String>,
    course: Option<String>,
    speed: Option<String>,
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

        let altitude = self.altitude.as_ref().unwrap().parse::<f64>().unwrap();

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
                latitude: aprs_parser::Latitude::new(self.lng).unwrap(),
                longitude: aprs_parser::Longitude::new(self.lat).unwrap(),
                precision: aprs_parser::Precision::HundredthMinute,
                symbol_table: symbol_chars[0],
                symbol_code: symbol_chars[1],
                comment: self.comment.to_owned().into_bytes(),
                cst: aprs_parser::AprsCst::Uncompressed,
            }),
        };

        crate::location::BalloonLocation {
            time: time.with_timezone(&chrono::Local),
            location: geo::point!(x: self.lng, y: self.lat),
            altitude: Some(altitude),
            data: crate::location::BalloonData::new(
                Some(aprs_packet),
                None,
                crate::location::LocationSource::AprsFi,
            ),
        }
    }
}
#[serde_with::serde_as]
#[derive(serde::Deserialize, Clone, Debug)]
pub struct AisData {
    mmsi: String,
    imo: Option<String>,
    vesselclass: Option<String>,
    navstat: Option<String>,
    heading: Option<String>,
    length: Option<String>,
    width: Option<String>,
    draught: Option<String>,
    ref_front: Option<String>,
    ref_left: Option<String>,
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
    #[serde(with = "crate::parse::deserialize_utc_timestamp_string")]
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
    #[serde(with = "crate::parse::deserialize_utc_datetime_string")]
    time: chrono::DateTime<chrono::Utc>,
    srccall: String,
    dst: String,
    message: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api() {
        if let Ok(api_key) = std::env::var("APRS_FI_API_KEY") {
            let callsigns = vec![
                String::from("W3EAX-10"),
                String::from("W3EAX-11"),
                String::from("W3EAX-13"),
                String::from("W3EAX-14"),
            ];

            let mut connection = AprsFiQuery::new(callsigns, api_key, None, None);
            println!("{:?}", connection.url());
            let packets = connection.retrieve_aprs_from_aprsfi().unwrap();

            assert!(!packets.is_empty());
        }
    }

    #[test]
    fn test_deserialize_location() {
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
    fn test_deserialize_aprs() {
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
    fn test_deserialize_ais() {
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
    #[should_panic]
    fn test_api_wrong_key() {
        let api_key = String::from("123456.abcdefghijklmno");
        let callsigns = vec![
            String::from("W3EAX-10"),
            String::from("W3EAX-11"),
            String::from("W3EAX-13"),
            String::from("W3EAX-14"),
        ];

        let mut connection = AprsFiQuery::new(callsigns, api_key, None, None);
        println!("{:?}", connection.url());
        let packets = connection.retrieve_aprs_from_aprsfi().unwrap();

        assert!(!packets.is_empty());
    }
}
