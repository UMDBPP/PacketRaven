#[cfg(feature = "aprsfi")]
pub mod aprs_fi;
pub mod file;
#[cfg(feature = "postgres")]
pub mod postgres;
#[cfg(feature = "serial")]
pub mod serial;
#[cfg(feature = "sondehub")]
pub mod sondehub;

lazy_static::lazy_static! {
    pub static ref USER_AGENT: String = format!("packetraven/{:}", env!("CARGO_PKG_VERSION"));
}

pub enum Connection {
    #[cfg(feature = "aprsfi")]
    AprsFi(aprs_fi::AprsFiQuery),
    #[cfg(feature = "sondehub")]
    SondeHub(sondehub::SondeHubQuery),
    AprsTextFile(file::AprsTextFile),
    GeoJsonFile(file::GeoJsonFile),
    #[cfg(feature = "postgres")]
    PacketDatabase(postgres::PacketDatabase),
    #[cfg(feature = "serial")]
    AprsSerial(serial::AprsSerial),
}

impl Connection {
    pub fn retrieve_packets(
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
    TooFrequent { connection: String, seconds: i64 } = "retrieval request exceeded request frequency set for {connection} ({seconds} s)",
    ApiError { message: String, url: String } = "API error parsing {url} - {message}",
    FailedToEstablish { connection: String, message: String } = "failed to establish connection to {connection}; {message}",
}
