fn first_available_port() -> String {
    // TODO iterate over baud rates
    let baud_rate = 9600;
    match serialport::available_ports() {
        Ok(available_ports) => {
            for available_port in available_ports {
                let connection_attempt =
                    serialport::new(&available_port.port_name, baud_rate).open();
                match connection_attempt {
                    Ok(successful) => {
                        return successful.name().unwrap();
                    }
                    Err(error) => {
                        panic!("{:}", error);
                    }
                }
            }
            panic!("{:}", "ports list is empty when it should not be");
        }
        Err(error) => {
            panic!("{:}", error);
        }
    }
}

#[derive(serde::Deserialize, Debug)]
pub struct AprsSerial {
    #[serde(default = "first_available_port")]
    pub port: String,
    pub baud_rate: u32,
}

impl AprsSerial {
    pub fn new(port: Option<String>, baud_rate: Option<u32>) -> Self {
        let baud = match baud_rate {
            Some(baud) => baud,
            None => 9600,
        };

        let mut port_name: String = String::new();
        match port {
            Some(name) => {
                port_name = serialport::new(&name, baud)
                    .open()
                    .unwrap_or_else(|_| {
                        panic!(
                            "error connecting to port {:?} at baud {:?}",
                            &name, baud_rate,
                        )
                    })
                    .name()
                    .unwrap();
            }
            None => {
                for available_port in serialport::available_ports().expect("no open ports found") {
                    let connection_attempt =
                        serialport::new(&available_port.port_name, baud).open();
                    match connection_attempt {
                        Ok(successful) => {
                            port_name = successful.name().unwrap();
                            break;
                        }
                        Err(error) => panic!("{:?}", error),
                    }
                }
            }
        }

        Self {
            port: port_name,
            baud_rate: baud,
        }
    }

    pub fn read_aprs_from_serial(
        &self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::Error> {
        let mut connection = serialport::new(&self.port, self.baud_rate).open().unwrap();

        let mut buffer = Vec::<u8>::new();
        match connection.read_to_end(&mut buffer) {
            Ok(_) => {
                let mut locations: Vec<crate::location::BalloonLocation> = vec![];
                for line in buffer.split(|a| a == &b'\n') {
                    locations.push(
                        crate::location::BalloonLocation::from_aprs_frame(line, None).unwrap(),
                    );
                }
                Ok(locations)
            }
            Err(error) => panic!("{:?}", error),
        }
    }
}

impl Default for AprsSerial {
    fn default() -> Self {
        Self::new(None, None)
    }
}
