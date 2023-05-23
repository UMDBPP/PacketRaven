use geo::GeodesicDistance;

pub type LocationTrack = Vec<crate::location::BalloonLocation>;

pub struct BalloonTrack {
    pub locations: LocationTrack,
    pub prediction: Option<LocationTrack>,
    pub name: String,
}

impl BalloonTrack {
    pub fn new(name: String) -> Self {
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
                        ((-ascent_rates(&self.locations).last().unwrap()
                            / altitudes.last().unwrap())
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
        let ascent_rates = ascent_rates(&self.locations);
        ascent_rates.iter().rev().take(2).all(|a| a > &0.2)
    }

    pub fn descending(&self) -> bool {
        let ascent_rates = ascent_rates(&self.locations);
        ascent_rates.iter().rev().take(2).all(|a| a < &0.2)
    }

    pub fn falling(&self) -> Option<crate::model::FreefallEstimate> {
        let last_location: &crate::location::BalloonLocation = self.locations.last().unwrap();

        if last_location.altitude.is_some() && self.descending() {
            let freefall_estimate = last_location.estimate_freefall();

            if let Some(last_ascent_rate) = ascent_rates(&self.locations).last() {
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

pub fn with_altitude(locations: &Vec<super::BalloonLocation>) -> Vec<super::BalloonLocation> {
    locations
        .into_iter()
        .filter(|location| location.altitude.is_some())
        .map(|location| location.to_owned())
        .collect()
}

pub fn intervals(locations: &Vec<super::BalloonLocation>) -> Vec<chrono::Duration> {
    let mut values = vec![];

    for index in 0..(locations.len() - 1) {
        let current = locations.get(index).unwrap();
        let next = locations.get(index + 1).unwrap();
        values.push(next.time - current.time);
    }

    values
}

pub fn altitudes(locations: &Vec<super::BalloonLocation>) -> Vec<f64> {
    locations
        .iter()
        .filter_map(|locations| locations.altitude)
        .collect()
}

pub fn ascents(locations: &Vec<super::BalloonLocation>) -> Vec<f64> {
    let mut values = vec![];

    let mut index = 0;
    let mut current = locations.first().unwrap();
    let mut next;
    loop {
        next = match locations.get(index + 1) {
            Some(next) => next,
            None => {
                break;
            }
        };

        values.push(next.altitude.unwrap() - current.altitude.unwrap());

        current = next;
        index += 1;
    }

    values
}

pub fn ascent_rates(locations: &Vec<super::BalloonLocation>) -> Vec<f64> {
    let mut values = vec![];

    let locations_with_altitude = with_altitude(locations);
    let intervals = intervals(&locations_with_altitude);
    for (index, ascent) in ascents(&locations_with_altitude).iter().enumerate() {
        values.push(ascent / intervals.get(index).unwrap().num_seconds() as f64);
    }

    values
}

pub fn overground_distances(locations: &Vec<super::BalloonLocation>) -> Vec<f64> {
    let mut values = vec![];

    let mut index = 0;
    let mut current = locations.first().unwrap();
    let mut next;
    loop {
        next = match locations.get(index + 1) {
            Some(next) => next,
            None => {
                break;
            }
        };

        values.push(current.location.geodesic_distance(&next.location));

        current = next;
        index += 1;
    }

    values
}

pub fn ground_speeds(locations: &Vec<super::BalloonLocation>) -> Vec<f64> {
    let mut values = vec![];

    let intervals = intervals(locations);
    for (index, distance) in overground_distances(locations).iter().enumerate() {
        values.push(distance / intervals.get(index).unwrap().num_seconds() as f64);
    }

    values
}
