#[derive(serde::Deserialize, Debug, PartialEq)]
pub struct AprsFiCredentials {
    pub api_key: String,
}

#[derive(serde::Deserialize, Debug, PartialEq)]
pub struct AprsIsCredentials {
    pub hostname: String,
}
