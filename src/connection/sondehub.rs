lazy_static::lazy_static! {
    static ref MINIMUM_ACCESS_INTERVAL: chrono::Duration = chrono::Duration::seconds(10);
}

#[derive(serde::Deserialize, Debug, PartialEq, Clone, Default)]
pub struct SondeHubQuery {
    pub start: Option<chrono::DateTime<chrono::Local>>,
    pub end: Option<chrono::DateTime<chrono::Local>>,
    pub callsigns: Option<Vec<String>>,
    #[serde(skip)]
    last_access: Option<chrono::DateTime<chrono::Local>>,
}

// https://generator.swagger.io/?url=https://raw.githubusercontent.com/projecthorus/sondehub-infra/main/swagger.yaml#/amateur/get_amateur_telemetry__payload_callsign_
impl SondeHubQuery {
    pub fn new(
        start: Option<chrono::DateTime<chrono::Local>>,
        end: Option<chrono::DateTime<chrono::Local>>,
        callsigns: Option<&Vec<String>>,
    ) -> Self {
        Self {
            start,
            end,
            callsigns: callsigns.map(|callsigns| callsigns.to_owned()),
            last_access: None,
        }
    }
}

impl SondeHubQuery {
    fn urls(&self) -> Result<Vec<String>, crate::connection::ConnectionError> {
        if let Some(callsigns) = &self.callsigns {
            let mut parameters = vec![];

            if let Some(end) = self.end {
                parameters.push(format!("datetime={:}", end.to_rfc3339()));
            }

            if let Some(last) = self.start.map(|start| {
                if let Some(end) = self.end {
                    end - start
                } else {
                    chrono::Local::now() - start
                }
            }) {
                parameters.push(format!("last={:}", last.num_seconds()));
            }

            let mut urls = vec![];
            for callsign in callsigns {
                let mut url = format!(
                    "https://api.v2.sondehub.org/amateur/telemetry/{:}",
                    callsign
                );
                if !parameters.is_empty() {
                    url += &format!("?{:}", parameters.join("&"));
                }

                urls.push(url);
            }

            Ok(urls)
        } else {
            Err(crate::connection::ConnectionError::FailedToEstablish {
                connection: "SondeHub".to_string(),
                message: "the API requires a list of callsigns".to_string(),
            })
        }
    }

    pub fn retrieve_locations_from_sondehub(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let now = chrono::Local::now();
        if let Some(last_access_time) = self.last_access {
            if now - last_access_time < *MINIMUM_ACCESS_INTERVAL {
                return Err(crate::connection::ConnectionError::TooFrequent {
                    connection: "SondeHub".to_string(),
                    duration: crate::utilities::duration_string(&MINIMUM_ACCESS_INTERVAL),
                });
            }
        }

        let mut balloon_locations: Vec<crate::location::BalloonLocation> = vec![];

        let client = reqwest::blocking::Client::builder()
            .user_agent(crate::connection::USER_AGENT.to_owned())
            .timeout(Some(std::time::Duration::from_secs(10)))
            .build()
            .unwrap();

        let urls = self.urls()?;
        for url in &urls {
            let response = client.get(url).send().expect(url);

            match response.status() {
                reqwest::StatusCode::OK => {
                    // deserialize JSON into struct
                    let locations: Vec<SondeHubLocation> = match response.json() {
                        Ok(object) => object,
                        Err(error) => {
                            return Err(crate::connection::ConnectionError::ApiError {
                                message: format!("{:?}", error),
                                url: url.to_owned(),
                            });
                        }
                    };
                    for location in locations {
                        balloon_locations.push(location.to_balloon_location());
                    }
                }
                other => {
                    return Err(crate::connection::ConnectionError::ApiError {
                        message: other.to_string(),
                        url: url.to_owned(),
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
    uploader_position: Option<String>,
    uploader_antenna: Option<String>,
    uploader_radio: Option<String>,
}
impl SondeHubLocation {
    pub fn to_balloon_location(&self) -> crate::location::BalloonLocation {
        let aprs_packet = match self.raw.as_ref() {
            Some(frame) => match aprs_parser::AprsPacket::decode_textual(frame.as_bytes()) {
                Ok(packet) => Some(packet),
                Err(_) => None,
            },
            None => None,
        };
        let time = self.datetime.to_owned();

        crate::location::BalloonLocation {
            location: crate::location::Location {
                time: time.with_timezone(&chrono::Local),
                coord: geo::coord! { x: self.lon, y: self.lat },
                altitude: Some(self.alt),
            },
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

        let mut connection = SondeHubQuery::new(
            Some(
                chrono::DateTime::parse_from_rfc3339("2022-07-31T00:00:00-04:00")
                    .unwrap()
                    .with_timezone(&chrono::Local),
            ),
            None,
            Some(&callsigns),
        );
        let packets = connection.retrieve_locations_from_sondehub().unwrap();

        assert!(!packets.is_empty());
    }

    #[test]
    fn test_aprs() {
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

        let SondeHubLocation { lon, .. } = response;
        assert_eq!(lon, -68.30413186813188);
    }

    #[test]
    fn test_lora() {
        let data = r#"
        {
            "software_name": "HAB Base",
            "software_version": "V1.7.2",
            "uploader_callsign": "F6ASP-Ttgo",
            "time_received": "2023-05-23T09:46:10Z",
            "payload_callsign": "TTGO",
            "datetime": "2023-05-23T09:46:09Z",
            "lat": 50.94162,
            "lon": 1.86,
            "alt": -29,
            "frequency": 434.7525,
            "modulation": "LoRa Mode 2",
            "snr": 11,
            "rssi": -94,
            "uploader_position": "50.9414,1.86021",
            "raw": "$$TTGO,83,09:46:09,50.94162,1.86000,-29,0,2,0,4149*EE2B",
            "user-agent": "Amazon CloudFront",
            "position": "50.94162,1.86",
            "uploader_alt": 15
        }
        "#;
        let response: SondeHubLocation = serde_json::from_str(data).unwrap();

        let SondeHubLocation { lon, .. } = response;
        assert_eq!(lon, 1.86);
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

        assert!(!response.is_empty());
    }

    #[test]
    fn test_api_nonexistent_callsign() {
        let callsigns = vec![String::from("nonexistent")];

        let mut connection = SondeHubQuery::new(None, None, Some(&callsigns));
        let packets = connection.retrieve_locations_from_sondehub().unwrap();

        assert!(packets.is_empty());
    }
}
