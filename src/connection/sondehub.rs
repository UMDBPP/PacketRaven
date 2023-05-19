lazy_static::lazy_static! {
    static ref MINIMUM_ACCESS_INTERVAL: chrono::Duration = chrono::Duration::seconds(10);
}

pub struct SondeHubQuery {
    pub callsigns: Vec<String>,
    pub start: Option<chrono::DateTime<chrono::Local>>,
    pub end: Option<chrono::DateTime<chrono::Local>>,
    last_access: Option<chrono::DateTime<chrono::Local>>,
}

// https://generator.swagger.io/?url=https://raw.githubusercontent.com/projecthorus/sondehub-infra/main/swagger.yaml#/amateur/get_amateur_telemetry__payload_callsign_
impl SondeHubQuery {
    pub fn new(
        callsigns: Vec<String>,
        start: Option<chrono::DateTime<chrono::Local>>,
        end: Option<chrono::DateTime<chrono::Local>>,
    ) -> Self {
        Self {
            callsigns,
            start,
            end,
            last_access: None,
        }
    }
}

impl SondeHubQuery {
    fn urls(&self) -> Vec<String> {
        let mut parameters = vec![];

        if let Some(end) = self.end {
            parameters.push(format!("datetime={:}", end.to_rfc3339()));
        }

        if let Some(start) = self.start {
            let last = self.start.map(|start| {
                if let Some(end) = self.end {
                    end - start
                } else {
                    chrono::Local::now() - start
                }
            });
            if let Some(last) = last {
                parameters.push(format!("last={:}", last.num_seconds()));
            }
        }

        let mut urls = vec![];
        for callsign in &self.callsigns {
            let mut url = format!(
                "https://api.v2.sondehub.org/amateur/telemetry/{:}",
                callsign
            );
            if !parameters.is_empty() {
                url += &format!("?{:}", parameters.join("&"));
            }

            urls.push(url);
        }

        urls
    }

    pub fn retrieve_locations_from_sondehub(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let now = chrono::Local::now();
        if let Some(last_access_time) = self.last_access {
            if now - last_access_time < *MINIMUM_ACCESS_INTERVAL {
                return Err(crate::connection::ConnectionError::TooFrequent {
                    connection: "SondeHub".to_string(),
                    seconds: (*MINIMUM_ACCESS_INTERVAL).num_seconds(),
                });
            }
        }

        let mut balloon_locations: Vec<crate::location::BalloonLocation> = vec![];

        let client = reqwest::blocking::Client::builder()
            .user_agent(crate::connection::USER_AGENT.to_owned())
            .build()
            .unwrap();

        let urls = self.urls();
        for url in &urls {
            let response = client.get(url).send().expect(url);

            match response.status() {
                reqwest::StatusCode::OK => {
                    // deserialize JSON into struct
                    let locations: Vec<SondeHubLocation> = match response.json() {
                        Ok(object) => object,
                        Err(error) => panic!("{:?} - {:?}", error, url),
                    };
                    for location in locations {
                        balloon_locations.push(location.to_balloon_location());
                    }
                }
                _ => {
                    return Err(crate::connection::ConnectionError::ApiError {
                        message: format!("API error: {:}", &url),
                    });
                }
            }
        }

        self.last_access = Some(now);
        Ok(balloon_locations)
    }
}

// https://github.com/projecthorus/sondehub-infra/wiki/%5BDRAFT%5D-Amateur-Balloon-Telemetry-Format
#[derive(serde::Deserialize)]
struct SondeHubLocation {
    software_name: String,
    software_version: String,
    uploader_callsign: String,
    time_received: chrono::DateTime<chrono::Local>,
    payload_callsign: String,
    datetime: chrono::DateTime<chrono::Local>,
    lat: f64,
    lon: f64,
    alt: f64,
    frame: Option<u64>,
    temp: Option<f64>,
    humidity: Option<f64>,
    pressure: Option<f64>,
    vel_h: Option<f64>,
    vel_v: Option<f64>,
    heading: Option<u64>,
    sats: Option<u8>,
    batt: Option<f64>,
    tx_frequency: Option<f64>,
    raw: Option<String>,
    modulation: Option<String>,
    moduleation_detail: Option<String>,
    baud_rate: Option<u64>,
    snr: Option<f64>,
    frequency: Option<f64>,
    rssi: Option<f64>,
    uploader_position: Option<[f64; 3]>,
    uploader_antenna: Option<String>,
    uploader_radio: Option<String>,
}
impl SondeHubLocation {
    pub fn to_balloon_location(&self) -> crate::location::BalloonLocation {
        let aprs_packet = if let Some(frame) = &self.raw {
            Some(
                match aprs_parser::AprsPacket::decode_textual(frame.as_bytes()) {
                    Ok(packet) => packet,
                    Err(error) => {
                        panic!("{:?}; {:?}", error, frame);
                    }
                },
            )
        } else {
            None
        };
        let time = self.datetime.to_owned();

        crate::location::BalloonLocation {
            time: time.with_timezone(&chrono::Local),
            location: geo::point!(x: self.lon, y: self.lat),
            altitude: Some(self.alt),
            data: crate::location::BalloonData::new(
                aprs_packet,
                None,
                crate::location::LocationSource::AprsFi,
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api() {
        let callsigns = vec![
            String::from("N1YIP-11"),
            String::from("W3EAX-10"),
            String::from("W3EAX-11"),
            String::from("W3EAX-13"),
            String::from("W3EAX-14"),
        ];

        let mut connection = SondeHubQuery::new(callsigns, None, None);
        let packets = connection.retrieve_locations_from_sondehub().unwrap();

        assert!(!packets.is_empty());
    }

    #[test]
    fn test_location() {
        let data = r#"
        {
            "software_name": "SondeHub APRS-IS Gateway",
            "software_version": "2023.04.16",
            "uploader_callsign": "KD1KE",
            "path": "WIDE2-1,qAR,KD1KE",
            "time_received": "2023-05-19T12:31:17.442024Z",
            "payload_callsign": "N1YIP-11",
            "datetime": "2023-05-19T12:31:15.000000Z",
            "lat": 44.90910256410256,
            "lon": -68.30413186813188,
            "alt": 10323.271200000001,
            "comment": "a=10326.1/R=47",
            "raw": "N1YIP-11>APZUME,WIDE2-1,qAR,KD1KE:/123115h4454.54N/06818.24WO097/034/A=033869!wYi!/a=10326.1/R=47",
            "aprs_tocall": "APZUME",
            "modulation": "APRS",
            "position": "44.90910256410256,-68.30413186813188"
        }
        "#;
        let response: SondeHubLocation = serde_json::from_str(data).unwrap();

        match response {
            SondeHubLocation { lon, .. } => {
                assert_eq!(lon, -68.30413186813188);
            }
            _ => panic!(),
        }
    }

    #[test]
    fn test_response() {
        let data = r#"
        [
            {
                "software_name": "SondeHub APRS-IS Gateway",
                "software_version": "2023.04.16",
                "uploader_callsign": "KD1KE",
                "path": "WIDE2-1,qAR,KD1KE",
                "time_received": "2023-05-19T12:31:17.442024Z",
                "payload_callsign": "N1YIP-11",
                "datetime": "2023-05-19T12:31:15.000000Z",
                "lat": 44.90910256410256,
                "lon": -68.30413186813188,
                "alt": 10323.271200000001,
                "comment": "a=10326.1/R=47",
                "raw": "N1YIP-11>APZUME,WIDE2-1,qAR,KD1KE:/123115h4454.54N/06818.24WO097/034/A=033869!wYi!/a=10326.1/R=47",
                "aprs_tocall": "APZUME",
                "modulation": "APRS",
                "position": "44.90910256410256,-68.30413186813188"
            },
            {
                "software_name": "SondeHub APRS-IS Gateway",
                "software_version": "2023.04.16",
                "uploader_callsign": "K1JAK-1",
                "path": "WIDE2-1,qAR,K1JAK-1",
                "time_received": "2023-05-19T12:30:17.440759Z",
                "payload_callsign": "N1YIP-11",
                "datetime": "2023-05-19T12:30:15.000000Z",
                "lat": 44.9100293040293,
                "lon": -68.31695604395604,
                "alt": 10057.1808,
                "comment": "a=10060.3/R=48",
                "raw": "N1YIP-11>APZUME,WIDE2-1,qAR,K1JAK-1:/123015h4454.60N/06819.01WO089/035/A=032996!w1d!/a=10060.3/R=48",
                "aprs_tocall": "APZUME",
                "modulation": "APRS",
                "position": "44.9100293040293,-68.31695604395604"
            }
        ]
        "#;
        let response: Vec<SondeHubLocation> = serde_json::from_str(data).unwrap();
    }

    #[test]
    fn test_api_nonexistent_callsign() {
        let api_key = String::from("123456.abcdefghijklmno");
        let callsigns = vec![String::from("nonexistent")];

        let mut connection = SondeHubQuery::new(callsigns, None, None);
        let packets = connection.retrieve_locations_from_sondehub().unwrap();

        assert!(packets.is_empty());
    }
}
