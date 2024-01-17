use chrono::Datelike;

const M_PER_FT: f64 = 0.3048;

fn parse_aprs_comment_altitude_feet(comment: &str) -> Result<u32, ParseError> {
    lazy_static::lazy_static! {
        static ref PATTERN: regex::Regex =
            regex::Regex::new(r"/A=(?P<altitude_feet>\d{6})").unwrap();
    }
    let captures = match PATTERN.captures(comment) {
        Some(captured_group) => captured_group,
        None => {
            return Err(ParseError::NoAltitudeInComment {
                comment: comment.to_string(),
            });
        }
    };
    Ok(captures["altitude_feet"].parse::<u32>().unwrap())
}

impl crate::location::BalloonLocation {
    pub fn from_aprs_frame(
        frame: &[u8],
        time: Option<chrono::DateTime<chrono::Local>>,
    ) -> Result<Self, ParseError> {
        let packet_time: chrono::DateTime<chrono::Local>;
        let longitude: f64;
        let latitude: f64;
        let altitude: f64;
        let comment: String;

        let packet = match aprs_parser::AprsPacket::decode_textual(frame) {
            Ok(packet) => packet,
            Err(error) => {
                return Err(ParseError::InvalidFrame {
                    error: error.to_string(),
                    frame: String::from_utf8(frame.to_vec()).unwrap(),
                });
            }
        };
        match &packet.data {
            aprs_parser::AprsData::Position(payload) => {
                comment = String::from_utf8(payload.comment.to_owned()).unwrap();
                let altitude_feet: f64;
                match payload.cst {
                    aprs_parser::AprsCst::CompressedSome { cs, .. } => match cs {
                        aprs_parser::AprsCompressedCs::Altitude(compressed_altitude) => {
                            altitude_feet = compressed_altitude.altitude_feet();
                        }
                        _ => {
                            return Err(ParseError::NoAltitudeInCompressedData);
                        }
                    },
                    aprs_parser::AprsCst::Uncompressed | aprs_parser::AprsCst::CompressedNone => {
                        altitude_feet = parse_aprs_comment_altitude_feet(&comment).unwrap() as f64
                    }
                }

                let now = chrono::offset::Utc::now();
                match time {
                    Some(time) => {
                        packet_time = time;
                    }
                    None => {
                        let naive_packet_time: chrono::NaiveDateTime;
                        match &payload.timestamp {
                            Some(timestamp) => {
                                let today = now.date_naive();
                                match timestamp {
                                    aprs_parser::Timestamp::DDHHMM(day, hour, minute) => {
                                        naive_packet_time = chrono::NaiveDate::from_ymd_opt(
                                            today.year(),
                                            today.month(),
                                            day.to_owned() as u32,
                                        )
                                        .unwrap()
                                        .and_hms_opt(
                                            hour.to_owned() as u32,
                                            minute.to_owned() as u32,
                                            0,
                                        )
                                        .unwrap();
                                    }
                                    aprs_parser::Timestamp::HHMMSS(hour, minute, second) => {
                                        naive_packet_time = today
                                            .and_hms_opt(
                                                hour.to_owned() as u32,
                                                minute.to_owned() as u32,
                                                second.to_owned() as u32,
                                            )
                                            .unwrap();
                                    }
                                    _ => {
                                        return Err(ParseError::InvalidTimestamp);
                                    }
                                }
                            }
                            None => {
                                naive_packet_time = now.naive_utc();
                            }
                        }
                        packet_time = chrono::DateTime::<chrono::Utc>::from_naive_utc_and_offset(
                            naive_packet_time,
                            chrono::Utc,
                        )
                        .with_timezone(&chrono::Local);
                    }
                }
                altitude = altitude_feet * M_PER_FT;
                longitude = payload.longitude.value();
                latitude = payload.latitude.value();
            }
            aprs_parser::AprsData::MicE(payload) => {
                comment = String::from_utf8(payload.comment.clone()).unwrap();
                let altitude_feet = parse_aprs_comment_altitude_feet(&comment).unwrap() as f64;

                match time {
                    Some(time) => {
                        packet_time = time;
                    }
                    None => match payload.current {
                        true => packet_time = chrono::offset::Local::now(),
                        false => {
                            return Err(ParseError::MicEPacketNotCurrent);
                        }
                    },
                }
                altitude = altitude_feet * M_PER_FT;
                longitude = payload.longitude.value();
                latitude = payload.latitude.value();
            }
            _ => {
                return Err(ParseError::NoPosition);
            }
        }

        Ok(Self {
            location: super::Location {
                time: packet_time,
                coord: geo::coord! { x: longitude, y: latitude },
                altitude: Some(altitude),
            },
            data: crate::location::BalloonData::new(
                None,
                Some(packet),
                None,
                Some(String::from_utf8(frame.to_vec()).unwrap()),
                crate::location::LocationSource::None,
            ),
        })
    }
}

custom_error::custom_error! {pub ParseError
    InvalidFrame { error: String, frame: String } = "{error}; \"{frame}\"",
    NoPosition = "packet does not have an encoded position",
    MicEPacketNotCurrent = "packet is not current, and no time was specified",
    InvalidTimestamp  = "could not parse packet timestamp",
    NoAltitudeInComment {comment: String} = "comment does not contain an altitude; {comment}",
    NoAltitudeInCompressedData = "compressed data does not contain altitude",
}

#[cfg(test)]
mod tests {
    use chrono::TimeZone;

    #[test]
    fn parse_compressed() {
        let frame = "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu".as_bytes();
        let packet_time_override = chrono::Local
            .with_ymd_and_hms(2019, 2, 3, 14, 36, 16)
            .unwrap();
        let packet =
            crate::location::BalloonLocation::from_aprs_frame(frame, Some(packet_time_override))
                .unwrap();

        assert_eq!(packet.location.time, packet_time_override);
        assert_eq!(
            packet.location.coord,
            geo::coord! { x: -77.48778502911327, y: 39.64903419561805 }
        );
        assert_eq!(packet.location.altitude.unwrap(), 16341.5472);

        match packet.data.aprs_packet {
            Some(aprs_parser::AprsPacket { from, via, data }) => {
                assert_eq!(from.to_string(), "W3EAX-13");
                assert_eq!(
                    via,
                    vec![
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_with_ssid("N3KTX", "10"),
                            true
                        ),
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_no_ssid("WIDE1"),
                            false
                        ),
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_with_ssid("WIDE2", "1"),
                            false
                        ),
                        aprs_parser::Via::QConstruct(aprs_parser::QConstruct::AR),
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_with_ssid("N3TJJ", "11"),
                            false
                        ),
                    ]
                );

                match data {
                    aprs_parser::AprsData::Position(payload) => {
                        assert_eq!(payload.to.call(), "APRS");
                        assert!(!payload.messaging_supported);
                        assert_eq!(payload.precision, aprs_parser::Precision::HundredthMinute);
                        assert_eq!(payload.symbol_table, '/');
                        assert_eq!(payload.symbol_code, 'O');
                        assert_eq!(
                            String::from_utf8(payload.comment).unwrap(),
                            "/A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu"
                        );
                    }
                    _ => panic!("position data not parsed"),
                }
            }
            _ => panic!("packet data not retrieved"),
        }
    }

    #[test]
    fn parse_no_compressed() {
        let frame = br"W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu";
        let packet_time_override = chrono::Local::now();
        let packet =
            crate::location::BalloonLocation::from_aprs_frame(frame, Some(packet_time_override))
                .unwrap();

        assert_eq!(packet.location.time, packet_time_override);
        assert_eq!(
            packet.location.coord,
            geo::coord! { x: -77.90921071284187, y: 39.7003564996876 }
        );
        assert_eq!(packet.location.altitude.unwrap(), 8201.8632);

        match packet.data.aprs_packet {
            Some(aprs_parser::AprsPacket { from, via, data }) => {
                assert_eq!(from.to_string(), "W3EAX-8");
                assert_eq!(
                    via,
                    vec![
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_with_ssid("WIDE1", "1"),
                            false
                        ),
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_with_ssid("WIDE2", "1"),
                            false
                        ),
                        aprs_parser::Via::QConstruct(aprs_parser::QConstruct::AR),
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_with_ssid("K3DO", "11"),
                            false
                        )
                    ]
                );

                match data {
                    aprs_parser::AprsData::Position(payload) => {
                        assert_eq!(payload.to.call(), "APRS");
                        assert!(!payload.messaging_supported);
                        assert_eq!(payload.precision, aprs_parser::Precision::HundredthMinute);
                        assert_eq!(payload.symbol_table, '/');
                        assert_eq!(payload.symbol_code, 'O');
                        assert_eq!(
                            String::from_utf8(payload.comment).unwrap(),
                            "/A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu"
                        );
                    }
                    _ => panic!("position data not parsed"),
                }
            }
            _ => panic!("packet data not retrieved"),
        }
    }

    #[test]
    fn parse_uncompressed() {
        let frame = br"ICA3D2>APRS,qAS,dl4mea:/074849h4821.61N\01224.49E^322/103/A=003054";
        let packet = crate::location::BalloonLocation::from_aprs_frame(frame, None).unwrap();

        assert_eq!(
            packet.location.time,
            chrono::DateTime::<chrono::Local>::from_naive_utc_and_offset(
                chrono::Utc::now()
                    .date_naive()
                    .and_hms_opt(7, 48, 49)
                    .unwrap(),
                chrono::FixedOffset::west_opt(4 * 60 * 60).unwrap(),
            )
        );
        assert_eq!(
            packet.location.coord,
            geo::coord! { x: 12.408166666666666, y: 48.36016666666667 }
        );
        assert_eq!(packet.location.altitude.unwrap(), 930.8592000000001);

        match packet.data.aprs_packet {
            Some(aprs_parser::AprsPacket { from, via, data }) => {
                assert_eq!(from.to_string(), "ICA3D2");
                assert_eq!(
                    via,
                    vec![
                        aprs_parser::Via::QConstruct(aprs_parser::QConstruct::AS),
                        aprs_parser::Via::Callsign(
                            aprs_parser::Callsign::new_no_ssid("dl4mea"),
                            false
                        )
                    ]
                );

                match data {
                    aprs_parser::AprsData::Position(payload) => {
                        assert_eq!(payload.to.call(), "APRS");
                        assert!(!payload.messaging_supported);
                        assert_eq!(payload.precision, aprs_parser::Precision::HundredthMinute);
                        assert_eq!(payload.symbol_table, '\\');
                        assert_eq!(payload.symbol_code, '^');
                        assert_eq!(
                            String::from_utf8(payload.comment).unwrap(),
                            "322/103/A=003054"
                        );
                    }
                    _ => panic!("position data not parsed"),
                }
            }
            _ => panic!("packet data not retrieved"),
        }
    }
}
