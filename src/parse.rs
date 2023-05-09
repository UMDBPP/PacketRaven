pub fn approx_equal(a: f64, b: f64, decimal_precision: u8) -> bool {
    let p = 10f64.powi(-(decimal_precision as i32));
    (a - b).abs() < p
}

pub mod deserialize_optional_local_datetime_string {
    use chrono::TimeZone;
    use serde::Deserialize;

    const FORMAT: &str = "%Y-%m-%d %H:%M:%S";

    pub fn serialize<S>(
        date: &Option<chrono::DateTime<chrono::Local>>,
        serializer: S,
    ) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        if let Some(ref date) = *date {
            return serializer.serialize_str(&format!("{:}", date.format(FORMAT)));
        }
        serializer.serialize_none()
    }

    pub fn deserialize<'de, D>(
        deserializer: D,
    ) -> Result<Option<chrono::DateTime<chrono::Local>>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let value: Option<String> = Option::deserialize(deserializer)?;
        if let Some(value) = value {
            return Ok(Some(
                chrono::Local
                    .datetime_from_str(&value, FORMAT)
                    .map_err(serde::de::Error::custom)?,
            ));
        }

        Ok(None)
    }
}

pub mod deserialize_utc_datetime_string {
    use chrono::TimeZone;
    use serde::Deserialize;

    const FORMAT: &str = "%Y-%m-%d %H:%M:%S";

    pub fn serialize<S>(
        date: &chrono::DateTime<chrono::Utc>,
        serializer: S,
    ) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let date = format!("{:}", date.format(FORMAT));
        serializer.serialize_str(&date)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<chrono::DateTime<chrono::Utc>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let value: String = String::deserialize(deserializer)?;
        chrono::Utc
            .datetime_from_str(&value, FORMAT)
            .map_err(serde::de::Error::custom)
    }
}

pub mod deserialize_local_datetime_string {
    use chrono::TimeZone;
    use serde::Deserialize;

    const FORMAT: &str = "%Y-%m-%d %H:%M:%S";

    pub fn serialize<S>(
        date: &chrono::DateTime<chrono::Local>,
        serializer: S,
    ) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let date = format!("{:}", date.format(FORMAT));
        serializer.serialize_str(&date)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<chrono::DateTime<chrono::Local>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let value: String = String::deserialize(deserializer)?;
        chrono::Local
            .datetime_from_str(&value, FORMAT)
            .map_err(serde::de::Error::custom)
    }
}

pub mod deserialize_utc_timestamp_string {
    use chrono::TimeZone;
    use serde::Deserialize;

    pub fn serialize<S>(
        date: &chrono::DateTime<chrono::Utc>,
        serializer: S,
    ) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let date = format!("{:}", date.timestamp());
        serializer.serialize_str(&date)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<chrono::DateTime<chrono::Utc>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let value: String = String::deserialize(deserializer)?;
        match chrono::Utc.timestamp_opt(value.parse::<i64>().unwrap(), 0) {
            chrono::LocalResult::Single(date) => Ok(date),
            _ => Err(serde::de::Error::custom("error parsing string")),
        }
    }
}
