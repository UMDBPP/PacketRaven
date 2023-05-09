pub mod aprs;
pub mod track;

#[derive(Clone, Debug)]
pub struct BalloonLocation {
    pub time: chrono::DateTime<chrono::Local>,
    pub location: geo::Point,
    pub altitude: Option<f64>,
    pub data: BalloonData,
}

impl PartialEq for BalloonLocation {
    fn eq(&self, other: &Self) -> bool {
        self.time.eq(&other.time)
            && crate::parse::approx_equal(self.location.x(), other.location.x(), 4)
            && crate::parse::approx_equal(self.location.y(), other.location.y(), 4)
            && match self.altitude {
                Some(altitude) => match other.altitude {
                    Some(other_altitude) => crate::parse::approx_equal(altitude, other_altitude, 4),
                    None => false,
                },
                None => false,
            }
    }
}

impl Eq for BalloonLocation {}

impl BalloonLocation {
    pub fn time_lag_of(&self, other: &Self) -> bool {
        self.time.ne(&other.time)
            && crate::parse::approx_equal(self.location.x(), other.location.x(), 4)
            && crate::parse::approx_equal(self.location.y(), other.location.y(), 4)
            && match self.altitude {
                Some(altitude) => match other.altitude {
                    Some(other_altitude) => crate::parse::approx_equal(altitude, other_altitude, 4),
                    None => false,
                },
                None => false,
            }
    }
}

#[derive(Clone, Default, Debug)]
pub struct BalloonData {
    pub aprs_packet: Option<aprs_parser::AprsPacket>,
    pub ais: Option<crate::connection::aprs_fi::AisData>,
    pub source: LocationSource,
    pub status: PacketStatus,
}

impl BalloonData {
    pub fn new(
        aprs_packet: Option<aprs_parser::AprsPacket>,
        ais: Option<crate::connection::aprs_fi::AisData>,
        source: LocationSource,
    ) -> Self {
        Self {
            aprs_packet,
            ais,
            source,
            status: PacketStatus::None,
        }
    }
}

#[derive(Clone, Default, Debug)]
pub enum LocationSource {
    AprsFi,
    Serial(String),
    TextFile(std::path::PathBuf),
    GeoJsonFile(std::path::PathBuf),
    Database(String),
    Prediction,
    #[default]
    None,
}

#[derive(Clone, Default, Debug)]
pub enum PacketStatus {
    Duplicate,
    TimeLaggedDuplicate,
    #[default]
    None,
}
