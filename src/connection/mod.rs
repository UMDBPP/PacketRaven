#[cfg(feature = "aprsfi")]
pub mod aprs_fi;
#[cfg(feature = "postgres")]
pub mod postgres;
#[cfg(feature = "sondehub")]
pub mod sondehub;
pub mod text;

lazy_static::lazy_static! {
    pub static ref USER_AGENT: String = format!("packetraven/{:}", env!("CARGO_PKG_VERSION"));
}

#[derive(Debug, Clone)]
pub enum Connection {
    AprsTextFile(text::file::AprsTextFile),
    GeoJsonFile(text::file::GeoJsonFile),
    #[cfg(feature = "serial")]
    AprsSerial(text::serial::AprsSerial),
    #[cfg(feature = "sondehub")]
    SondeHub(sondehub::SondeHubQuery),
    #[cfg(feature = "aprsfi")]
    AprsFi(aprs_fi::AprsFiQuery),
    #[cfg(feature = "postgres")]
    PacketDatabase(postgres::DatabaseCredentials),
}

impl Connection {
    pub fn retrieve_locations(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, ConnectionError> {
        match self {
            #[cfg(feature = "aprsfi")]
            Self::AprsFi(connection) => connection.retrieve_aprs_from_aprsfi(),
            #[cfg(feature = "sondehub")]
            Self::SondeHub(connection) => connection.retrieve_locations_from_sondehub(),
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
    ReadFailure { connection: String, message: String } = "failed to read from {connection} - {message}",
    TooFrequent { connection: String, duration: String } = "retrieval request exceeded request frequency set for {connection} ({duration})",
    ApiError { message: String, url: String } = "API error parsing {url} - {message}",
    FailedToEstablish { connection: String, message: String } = "failed to establish connection to {connection}; {message}",
}
