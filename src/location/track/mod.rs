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
        if !self.contains(&location) {
            let needs_sorting = match self.locations.last() {
                Some(current) => current.location.time > location.location.time,
                None => false,
            };
            self.locations.push(location);
            if needs_sorting {
                self.locations
                    .sort_by_key(|location| location.location.time);
            }
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
            let mut altitudes = vec![];
            for location in &self.locations {
                if let Some(altitude) = location.location.altitude {
                    altitudes.push(altitude);
                }
            }
            if altitudes.len() > 1 {
                Some(chrono::Duration::milliseconds(
                    ((-ascent_rates(&self.locations).last().unwrap() / altitudes.last().unwrap())
                        * 1000.0) as i64,
                ))
            } else {
                None
            }
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

        if last_location.location.altitude.is_some() && self.descending() {
            let freefall_estimate = last_location.location.estimate_freefall();

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
}

pub fn with_altitude(locations: &[super::BalloonLocation]) -> Vec<super::BalloonLocation> {
    locations
        .iter()
        .filter_map(|location| {
            if location.location.altitude.is_some() {
                Some(location.to_owned())
            } else {
                None
            }
        })
        .collect()
}

pub fn intervals(locations: &[super::BalloonLocation]) -> Vec<chrono::Duration> {
    let mut values = vec![];

    let mut index = 0;
    let mut current = match locations.first() {
        Some(first) => first,
        None => return values,
    };
    let mut next;
    loop {
        next = match locations.get(index + 1) {
            Some(next) => next,
            None => {
                break;
            }
        };

        values.push(next.location.time - current.location.time);

        current = next;
        index += 1;
    }

    values
}

pub fn altitudes(locations: &[super::BalloonLocation]) -> Vec<f64> {
    locations
        .iter()
        .filter_map(|locations| locations.location.altitude)
        .collect()
}

pub fn ascents(locations: &[super::BalloonLocation]) -> Vec<f64> {
    let mut values = vec![];

    let mut index = 0;
    let mut current = match locations.first() {
        Some(first) => first,
        None => return values,
    };
    let mut next;
    loop {
        next = match locations.get(index + 1) {
            Some(next) => next,
            None => {
                break;
            }
        };

        values.push(next.location.altitude.unwrap() - current.location.altitude.unwrap());

        current = next;
        index += 1;
    }

    values
}

pub fn ascent_rates(locations: &[super::BalloonLocation]) -> Vec<f64> {
    let mut values = vec![];

    let locations_with_altitude = with_altitude(locations);
    let intervals = intervals(locations_with_altitude.as_slice());
    for (index, ascent) in ascents(&locations_with_altitude).iter().enumerate() {
        values.push(ascent / intervals.get(index).unwrap().num_seconds() as f64);
    }

    values
        .into_iter()
        .filter(|value| value.is_finite())
        .collect()
}

pub fn overground_distances(locations: &[super::BalloonLocation]) -> Vec<f64> {
    let mut values = vec![];

    let mut index = 0;
    let mut current = match locations.first() {
        Some(first) => first,
        None => return values,
    };
    let mut next;
    loop {
        next = match locations.get(index + 1) {
            Some(next) => next,
            None => {
                break;
            }
        };

        let current_point: geo::Point = current.location.coord.into();
        let next_point: geo::Point = next.location.coord.into();

        values.push(current_point.geodesic_distance(&next_point));

        current = next;
        index += 1;
    }

    values
}

pub fn ground_speeds(locations: &[super::BalloonLocation]) -> Vec<f64> {
    let mut values = vec![];

    let intervals = intervals(locations);
    for (index, distance) in overground_distances(locations).iter().enumerate() {
        values.push(distance / intervals.get(index).unwrap().num_seconds() as f64);
    }

    values
        .into_iter()
        .filter(|value| value.is_finite())
        .collect()
}
