#[cfg(feature = "aprsfi")]
pub mod aprs_fi;
pub mod file;
#[cfg(feature = "postgres")]
pub mod postgres;
#[cfg(feature = "serial")]
pub mod serial;

pub enum Connection {
    #[cfg(feature = "aprsfi")]
    AprsFi(crate::connection::aprs_fi::AprsFiQuery),
    AprsTextFile(crate::connection::file::AprsTextFile),
    GeoJsonFile(crate::connection::file::GeoJsonFile),
    #[cfg(feature = "postgres")]
    PacketDatabase(crate::connection::postgres::PacketDatabase),
    #[cfg(feature = "serial")]
    AprsSerial(crate::connection::serial::AprsSerial),
}

impl Connection {
    pub fn retrieve_packets(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, ConnectionError> {
        match self {
            #[cfg(feature = "aprsfi")]
            Self::AprsFi(connection) => connection.retrieve_aprs_from_aprsfi(),
            Self::AprsTextFile(connection) => connection.read_aprs_from_file(),
            Self::GeoJsonFile(connection) => connection.read_locations_from_geojson(),
            #[cfg(feature = "postgres")]
            Self::PacketDatabase(connection) => connection.retrieve_locations_from_database(),
            #[cfg(feature = "serial")]
            Self::AprsSerial(connection) => connection.read_aprs_from_serial(),
        }
    }
}

custom_error::custom_error! {pub ConnectionError
    TooFrequent= "retrieval request exceeded request frequency",
    ApiError {message:String}="{message}",
    FailedToEstablish {message:String}="failed to establish connection; {message}",
    Passthrough{message:String} = "{message}"
}
