#[serde_with::serde_as]
#[derive(serde::Deserialize, Clone, Debug, PartialEq)]
pub struct AisData {
    pub mmsi: String,
    pub imo: Option<String>,
    pub vesselclass: Option<String>,
    pub navstat: Option<String>,
    pub heading: Option<String>,
    pub length: Option<String>,
    pub width: Option<String>,
    pub draught: Option<String>,
    pub ref_front: Option<String>,
    pub ref_left: Option<String>,
}
