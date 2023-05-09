use geo::GeodesicDistance;

pub struct BalloonTrack {
    pub name: String,
    pub locations: Vec<crate::location::BalloonLocation>,
    pub attributes: BalloonTrackAttributes,
}

impl BalloonTrack {
    pub fn new(name: String) -> Self {
        Self {
            name,
            locations: vec![],
            attributes: BalloonTrackAttributes::new(),
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

    pub fn time_to_ground(&self) -> Option<chrono::Duration> {
        if self.descending() {
            if let Some(freefall_estimate) = self.falling() {}
        }
        None
    }

    pub fn descending(&self) -> bool {
        let ascent_rates = self.ascent_rates();
        ascent_rates.iter().rev().take(2).all(|a| a < &0.0)
    }

    pub fn falling(&self) -> Option<crate::model::FreefallEstimate> {
        let current_location: &crate::location::BalloonLocation = self.locations.last().unwrap();

        if current_location.altitude.is_some() {
            let freefall_estimate = current_location.estimate_freefall();

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
    pub prediction: bool,
}

impl BalloonTrackAttributes {
    pub fn new() -> Self {
        Self {
            callsign: None,
            prediction: false,
        }
    }
}
