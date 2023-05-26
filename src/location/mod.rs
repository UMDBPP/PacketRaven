pub mod ais;
pub mod aprs;
pub mod track;

#[derive(serde::Deserialize, Clone, Debug)]
pub struct Location {
    #[serde(with = "crate::utilities::local_datetime_string")]
    pub time: chrono::DateTime<chrono::Local>,
    pub coord: geo::Coord,
    pub altitude: Option<f64>,
}

impl PartialEq for Location {
    fn eq(&self, other: &Self) -> bool {
        self.time.eq(&other.time)
            && crate::utilities::approx_equal(self.coord.x, other.coord.x, 4)
            && crate::utilities::approx_equal(self.coord.y, other.coord.y, 4)
            && match self.altitude {
                Some(altitude) => match other.altitude {
                    Some(other_altitude) => {
                        crate::utilities::approx_equal(altitude, other_altitude, 4)
                    }
                    None => false,
                },
                None => match other.altitude {
                    None => true,
                    _ => false,
                },
            }
    }
}

impl Eq for Location {}

impl Location {
    pub fn time_lag_of(&self, other: &Self) -> bool {
        self.time.ne(&other.time)
            && crate::utilities::approx_equal(self.coord.x, other.coord.x, 4)
            && crate::utilities::approx_equal(self.coord.y, other.coord.y, 4)
            && match self.altitude {
                Some(altitude) => match other.altitude {
                    Some(other_altitude) => {
                        crate::utilities::approx_equal(altitude, other_altitude, 4)
                    }
                    None => false,
                },
                None => false,
            }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct BalloonLocation {
    pub location: Location,
    pub data: BalloonData,
}

#[derive(Clone, Default, Debug, PartialEq)]
pub struct BalloonData {
    pub callsign: Option<String>,
    pub aprs_packet: Option<aprs_parser::AprsPacket>,
    pub ais: Option<ais::AisData>,
    pub source: LocationSource,
    pub raw: Option<String>,
    pub status: PacketStatus,
}

impl BalloonData {
    pub fn new(
        callsign: Option<String>,
        aprs_packet: Option<aprs_parser::AprsPacket>,
        ais: Option<ais::AisData>,
        raw: Option<String>,
        source: LocationSource,
    ) -> Self {
        let mut callsign = callsign;
        if callsign.is_none() {
            if let Some(aprs_packet) = &aprs_packet {
                callsign = Some(aprs_packet.from.to_string());
            } else if let Some(ais) = &ais {
                callsign = Some(ais.mmsi.to_owned());
            }
        }

        Self {
            callsign,
            aprs_packet,
            ais,
            raw,
            source,
            status: PacketStatus::None,
        }
    }
}

#[derive(Clone, Default, Debug, PartialEq)]
pub enum LocationSource {
    AprsFi,
    Serial(String),
    TextFile(String),
    GeoJsonFile(String),
    Database(String),
    Prediction,
    #[default]
    None,
}

#[derive(Clone, Default, Debug, PartialEq)]
pub enum PacketStatus {
    Duplicate,
    TimeLaggedDuplicate,
    #[default]
    None,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_location() {
        let path = format!(
            "{:}/{:}",
            env!("CARGO_MANIFEST_DIR"),
            "data/test_location.yaml"
        );

        #[derive(serde::Deserialize)]
        struct Locations {
            locations: Vec<Location>,
        }

        let file = std::fs::File::open(path).unwrap();
        let locations: Locations = serde_yaml::from_reader(file).unwrap();

        assert!(!locations.locations.is_empty());
    }
}
