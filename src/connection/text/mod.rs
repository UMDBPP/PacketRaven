pub mod file;
#[cfg(feature = "serial")]
pub mod serial;

#[derive(serde::Deserialize, Debug, PartialEq, Clone, serde::Serialize)]
#[serde(untagged)]
pub enum TextStream {
    AprsTextFile(file::AprsTextFile),
    GeoJsonFile(file::GeoJsonFile),
    #[cfg(feature = "serial")]
    AprsSerial(serial::AprsSerial),
}
