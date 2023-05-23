use std::io::prelude::BufRead;

use chrono::{TimeZone, Timelike};

#[derive(serde::Deserialize, Debug)]
pub struct AprsTextFile {
    pub path: std::path::PathBuf,
}

impl AprsTextFile {
    pub fn new(path: std::path::PathBuf) -> Result<Self, crate::connection::ConnectionError> {
        if path.exists() || url::Url::parse(path.to_str().unwrap()).is_ok() {
            Ok(Self { path })
        } else {
            Err(crate::connection::ConnectionError::FailedToEstablish {
                connection: path.to_str().unwrap().to_string(),
                message: "path does not exist".to_string(),
            })
        }
    }
}

fn read_lines(
    path: &std::path::PathBuf,
) -> Result<Vec<String>, crate::connection::ConnectionError> {
    let mut lines: Vec<String> = vec![];
    match url::Url::parse(path.to_str().unwrap()) {
        Ok(url) => {
            let response = reqwest::blocking::get(url).expect("error retrieving remote file");
            let text = response.text().expect("error parsing remote file");
            for line in text.split('\n') {
                lines.push(line.to_string());
            }
        }
        Err(error) => match error {
            url::ParseError::RelativeUrlWithoutBase => match std::fs::File::open(path) {
                Ok(file) => {
                    let reader = std::io::BufReader::new(file);
                    for line in reader.lines() {
                        lines.push(line.unwrap());
                    }
                }
                Err(error) => {
                    return Err(crate::connection::ConnectionError::FailedToEstablish {
                        connection: path.to_str().unwrap().to_string(),
                        message: error.to_string(),
                    });
                }
            },
            _ => {
                return Err(crate::connection::ConnectionError::FailedToEstablish {
                    connection: path.to_str().unwrap().to_string(),
                    message: error.to_string(),
                });
            }
        },
    }

    Ok(lines)
}

impl AprsTextFile {
    pub fn read_aprs_from_file(
        &self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let lines = match read_lines(&self.path) {
            Ok(lines) => lines,
            Err(error) => match error {
                crate::connection::ConnectionError::FailedToEstablish { .. } => {
                    return Err(error);
                }
                _ => {
                    return Err(crate::connection::ConnectionError::FailedToEstablish {
                        connection: "file".to_string(),
                        message: error.to_string(),
                    })
                }
            },
        };

        let mut locations: Vec<crate::location::BalloonLocation> = vec![];
        for line in lines {
            let location: crate::location::BalloonLocation;
            if line.contains(": ") {
                let mut parts = vec![];
                parts.extend(line.splitn(2, ": "));
                match chrono::DateTime::parse_from_rfc3339(parts[0]) {
                    Ok(time) => {
                        location = crate::location::BalloonLocation::from_aprs_frame(
                            parts[1].as_bytes(),
                            Some(time.with_timezone(&chrono::Local)),
                        )
                        .unwrap();
                    }
                    Err(_) => {
                        location = match crate::location::BalloonLocation::from_aprs_frame(
                            parts[1].as_bytes(),
                            None,
                        ) {
                            Ok(location) => location,
                            Err(_) => continue,
                        };
                    }
                }
            } else {
                location = crate::location::BalloonLocation::from_aprs_frame(line.as_bytes(), None)
                    .unwrap();
            }

            locations.push(location);
        }
        Ok(locations)
    }
}

#[derive(serde::Deserialize, Debug)]
pub struct GeoJsonFile {
    pub path: std::path::PathBuf,
}

impl GeoJsonFile {
    pub fn new(path: std::path::PathBuf) -> Self {
        Self { path }
    }
}

impl GeoJsonFile {
    pub fn read_locations_from_geojson(
        &self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let lines = read_lines(&self.path).unwrap();
        let contents = lines.join("\n");
        let parsed = contents.parse::<geojson::GeoJson>().unwrap();

        let mut locations: Vec<crate::location::BalloonLocation> = vec![];
        if let geojson::GeoJson::FeatureCollection(ref collection) = parsed {
            for feature in &collection.features {
                if let Some(ref geometry) = feature.geometry {
                    if let geojson::Value::Point(point) = &geometry.value {
                        let properties = feature.properties.as_ref().unwrap();

                        let time = match properties.get("time").unwrap() {
                            serde_json::Value::String(time) => {
                                chrono::DateTime::parse_from_rfc3339(time.as_ref())
                                    .unwrap()
                                    .with_timezone(&chrono::Local)
                            }
                            serde_json::Value::Number(time) => chrono::Local
                                .timestamp_opt(time.as_i64().unwrap(), 0)
                                .unwrap()
                                .with_timezone(&chrono::Local),
                            _ => continue,
                        };

                        let altitude = if point.len() > 2 {
                            Some(point[2])
                        } else {
                            None
                        };

                        let aprs_packet = if properties.contains_key("from") {
                            let comment = if properties.contains_key("comment") {
                                match properties.get("comment").unwrap() {
                                    serde_json::Value::String(comment) => comment.to_owned(),
                                    _ => continue,
                                }
                            } else {
                                String::new()
                            };

                            Some(aprs_parser::AprsPacket {
                                from: match properties.get("from").unwrap() {
                                    serde_json::Value::String(callsign) => {
                                        aprs_parser::Callsign::new(callsign).unwrap()
                                    }
                                    _ => continue,
                                },
                                via: vec![],
                                data: aprs_parser::AprsData::Position(aprs_parser::AprsPosition {
                                    to: match properties.get("to").unwrap() {
                                        serde_json::Value::String(callsign) => {
                                            aprs_parser::Callsign::new(callsign).unwrap()
                                        }
                                        _ => continue,
                                    },
                                    timestamp: aprs_parser::Timestamp::new_hms(
                                        time.hour() as u8,
                                        time.minute() as u8,
                                        time.second() as u8,
                                    ),
                                    messaging_supported: false,
                                    latitude: aprs_parser::Latitude::new(point[0]).unwrap(),
                                    longitude: aprs_parser::Longitude::new(point[1]).unwrap(),
                                    precision: aprs_parser::Precision::HundredthMinute,
                                    symbol_table: '/',
                                    symbol_code: 'O',
                                    comment: comment.into_bytes(),
                                    cst: aprs_parser::AprsCst::Uncompressed,
                                }),
                            })
                        } else {
                            None
                        };

                        let location = crate::location::BalloonLocation {
                            time,
                            location: geo::point!(x: point[0], y: point[1]),
                            altitude,
                            data: crate::location::BalloonData::new(
                                aprs_packet,
                                None,
                                crate::location::LocationSource::TextFile(self.path.to_owned()),
                            ),
                        };
                        locations.push(location);
                    }
                }
            }
        }

        Ok(locations)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_aprs_from_url() {
        let url = std::path::PathBuf::from(
            "http://bpp.umd.edu/archives/Launches/NS-111_2022_07_31/APRS/W3EAX-11%20raw.txt",
        );

        let connection = AprsTextFile::new(url).unwrap();

        let packets = connection.read_aprs_from_file().unwrap();

        assert!(!packets.is_empty());
    }

    #[test]
    fn test_aprs_from_file() {
        let path = std::path::PathBuf::from(format!(
            "{:}/{:}",
            env!("CARGO_MANIFEST_DIR"),
            "data/aprs/W3EAX-8_raw_NS-111.txt"
        ));

        let connection = AprsTextFile::new(path).unwrap();

        let packets = connection.read_aprs_from_file().unwrap();

        assert!(!packets.is_empty());
    }
}
