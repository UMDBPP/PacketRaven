#[derive(serde::Deserialize)]
pub struct PlotsConfiguration {
    pub altitude: Option<bool>,
    pub ascent_rate: Option<bool>,
    pub ground_speed: Option<bool>,
}
