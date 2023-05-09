pub mod aprs_fi;
pub mod file;
pub mod postgres;
pub mod serial;

pub enum Connection {
    AprsFi(crate::connection::aprs_fi::AprsFiQuery),
    AprsTextFile(crate::connection::file::AprsTextFile),
    GeoJsonFile(crate::connection::file::GeoJsonFile),
    PacketDatabase(crate::connection::postgres::PacketDatabase),
    AprsSerial(crate::connection::serial::AprsSerial),
}

impl Connection {
    pub fn retrieve_packets(&mut self) -> Vec<crate::location::BalloonLocation> {
        match self {
            Self::AprsFi(connection) => connection.retrieve_aprs_from_aprsfi(),
            Self::AprsTextFile(connection) => connection.read_aprs_from_file(),
            Self::GeoJsonFile(connection) => connection.read_locations_from_geojson(),
            Self::PacketDatabase(connection) => connection.retrieve_locations_from_database(),
            Self::AprsSerial(connection) => connection.read_aprs_from_serial(),
        }
    }
}
