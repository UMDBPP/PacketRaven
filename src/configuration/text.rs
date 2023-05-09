#[derive(serde::Deserialize, Debug, PartialEq)]
pub struct TextStreamConfiguration {
    pub locations: Vec<std::path::PathBuf>,
}
