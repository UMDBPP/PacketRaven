use geo::GeodesicDistance;

pub type LocationTrack = Vec<crate::location::BalloonLocation>;

pub struct BalloonTrack {
    pub locations: LocationTrack,
    pub prediction: Option<LocationTrack>,
    pub name: String,
}

impl BalloonTrack {
    pub fn new(name: String, callsign: Option<String>) -> Self {
        Self {
            locations: vec![],
            prediction: None,
            name,
        }
    }

    pub fn push(&mut self, location: crate::location::BalloonLocation) {
        let needs_sorting = match self.locations.last() {
            Some(current) => current.time > location.time,
            None => false,
        };
        self.locations.push(location);
        if needs_sorting {
            self.locations.sort_by_key(|location| location.time);
        }
    }

    pub fn contains(&self, location: &crate::location::BalloonLocation) -> bool {
        for existing_location in &self.locations {
            if location.eq(existing_location) {
                return true;
            }
        }
        false
    }

    pub fn intervals(&self) -> Vec<chrono::Duration> {
        let mut values = vec![];

        for index in 0..(self.locations.len() - 1) {
            let current = self.locations.get(index).unwrap();
            let next = self.locations.get(index + 1).unwrap();
            values.push(next.time - current.time);
        }

        values
    }

    pub fn ascents(&self) -> Vec<f64> {
        let mut values = vec![];

        for index in 0..(self.locations.len() - 1) {
            let current = self.locations.get(index).unwrap();
            let next = self.locations.get(index + 1).unwrap();
            values.push(
                next.altitude.expect("location has no altitude")
                    - current.altitude.expect("location has no altitude"),
            );
        }

        values
    }

    pub fn ascent_rates(&self) -> Vec<f64> {
        let mut values = vec![];
        let interval = self.intervals();

        for (index, ascent) in self.ascents().iter().enumerate() {
            values.push(ascent / interval.get(index).unwrap().num_seconds() as f64);
        }

        values
    }

    pub fn overground_distances(&self) -> Vec<f64> {
        let mut values = vec![];

        for index in 0..(self.locations.len() - 1) {
            let current = self.locations.get(index).unwrap();
            let next = self.locations.get(index + 1).unwrap();
            values.push(current.location.geodesic_distance(&next.location));
        }

        values
    }

    pub fn ground_speeds(&self) -> Vec<f64> {
        let mut values = vec![];
        let interval = self.intervals();

        for (index, distance) in self.overground_distances().iter().enumerate() {
            values.push(distance / interval.get(index).unwrap().num_seconds() as f64);
        }

        values
    }

    pub fn estimated_time_to_ground(&self) -> Option<chrono::Duration> {
        if !self.locations.is_empty() && self.descending() {
            if let Some(freefall_estimate) = self.falling() {
                Some(freefall_estimate.time_to_ground)
            } else {
                let mut altitudes = vec![];
                for location in &self.locations {
                    if let Some(altitude) = location.altitude {
                        altitudes.push(altitude);
                    }
                }
                if altitudes.len() > 1 {
                    Some(chrono::Duration::milliseconds(
                        ((-self.ascent_rates().last().unwrap() / altitudes.last().unwrap())
                            * 1000.0) as i64,
                    ))
                } else {
                    None
                }
            }
        } else {
            None
        }
    }

    pub fn predicted_time_to_ground(&self) -> Option<chrono::Duration> {
        if let Some(prediction) = &self.prediction {
            Some(prediction.last().unwrap().time - chrono::Local::now())
        } else {
            None
        }
    }

    pub fn ascending(&self) -> bool {
        let ascent_rates = self.ascent_rates();
        ascent_rates.iter().rev().take(2).all(|a| a > &0.2)
    }

    pub fn descending(&self) -> bool {
        let ascent_rates = self.ascent_rates();
        ascent_rates.iter().rev().take(2).all(|a| a < &0.2)
    }

    pub fn falling(&self) -> Option<crate::model::FreefallEstimate> {
        let last_location: &crate::location::BalloonLocation = self.locations.last().unwrap();

        if last_location.altitude.is_some() && self.descending() {
            let freefall_estimate = last_location.estimate_freefall();

            if let Some(last_ascent_rate) = self.ascent_rates().last() {
                if (last_ascent_rate - freefall_estimate.ascent_rate)
                    < freefall_estimate.ascent_rate_uncertainty
                {
                    Some(freefall_estimate)
                } else {
                    None
                }
            } else {
                None
            }
        } else {
            None
        }
    }

    pub fn interpolate(&self, time: chrono::NaiveDateTime) -> crate::location::BalloonLocation {
        // TODO
        unimplemented!()
    }
}

pub struct BalloonTrackAttributes {
    pub callsign: Option<String>,
}

impl BalloonTrackAttributes {
    pub fn new() -> Self {
        Self { callsign: None }
    }
}
