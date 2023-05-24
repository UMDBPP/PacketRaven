pub fn approx_equal(a: f64, b: f64, decimal_precision: u8) -> bool {
    let p = 10f64.powi(-(decimal_precision as i32));
    (a - b).abs() < p
}

pub mod optional_local_datetime_string {
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
                match chrono::Local.datetime_from_str(&value, FORMAT) {
                    Ok(datetime) => datetime,
                    Err(_) => chrono::NaiveDate::parse_from_str(&value, "%Y-%m-%d")
                        .map_err(serde::de::Error::custom)?
                        .and_hms_opt(0, 0, 0)
                        .unwrap()
                        .and_local_timezone(chrono::Local)
                        .unwrap(),
                },
            ));
        }

        Ok(None)
    }
}

pub mod utc_datetime_string {
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
        Ok(match chrono::Utc.datetime_from_str(&value, FORMAT) {
            Ok(datetime) => datetime,
            Err(_) => chrono::NaiveDate::parse_from_str(&value, "%Y-%m-%d")
                .map_err(serde::de::Error::custom)?
                .and_hms_opt(0, 0, 0)
                .unwrap()
                .and_local_timezone(chrono::Local)
                .unwrap()
                .with_timezone(&chrono::Utc),
        })
    }
}

pub mod local_datetime_string {
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
        Ok(match chrono::Local.datetime_from_str(&value, FORMAT) {
            Ok(datetime) => datetime,
            Err(_) => chrono::NaiveDate::parse_from_str(&value, "%Y-%m-%d")
                .map_err(serde::de::Error::custom)?
                .and_hms_opt(0, 0, 0)
                .unwrap()
                .and_local_timezone(chrono::Local)
                .unwrap(),
        })
    }
}

pub mod utc_timestamp_string {
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

pub mod optional_f64_string {
    use serde::Deserialize;
    use serde_json::Value;

    pub fn serialize<S>(option: &Option<f64>, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        if let Some(value) = *option {
            return serializer.serialize_f64(value);
        }
        serializer.serialize_none()
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Option<f64>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let option: Option<Value> = Option::deserialize(deserializer)?;
        if let Some(value) = option {
            if let Some(value) = value.as_str() {
                if let Ok(value) = value.parse::<f64>() {
                    Ok(Some(value))
                } else {
                    Ok(None)
                }
            } else {
                Ok(value.as_f64())
            }
        } else {
            Ok(None)
        }
    }
}

pub mod optional_u64_string {
    use serde::Deserialize;
    use serde_json::Value;

    pub fn serialize<S>(option: &Option<u64>, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        if let Some(value) = *option {
            return serializer.serialize_u64(value);
        }
        serializer.serialize_none()
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Option<u64>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let option: Option<Value> = Option::deserialize(deserializer)?;
        if let Some(value) = option {
            if let Some(value) = value.as_str() {
                if let Ok(value) = value.parse::<u64>() {
                    Ok(Some(value))
                } else {
                    Ok(None)
                }
            } else {
                Ok(value.as_u64())
            }
        } else {
            Ok(None)
        }
    }
}

pub fn duration_string(duration: chrono::Duration) -> String {
    let mut parts = vec![];

    let weeks = duration.num_weeks().abs();
    let days = duration.num_days().abs() % 7;
    let hours = duration.num_hours().abs() % 24;
    let minutes = duration.num_minutes().abs() % 60;
    let seconds = duration.num_seconds().abs() % 60;

    if weeks > 0 {
        parts.push(format!("{:}w", weeks));
    }

    if days > 0 {
        parts.push(format!("{:}d", days));
    }

    if hours > 0 {
        parts.push(format!("{:}h", hours));
    }

    if minutes > 0 {
        parts.push(format!("{:}m", minutes));
    }

    if seconds > 0 {
        parts.push(format!("{:}s", seconds));
    }

    if duration < chrono::Duration::zero() {
        parts.push("ago".to_string());
    }

    parts.join(" ")
}
