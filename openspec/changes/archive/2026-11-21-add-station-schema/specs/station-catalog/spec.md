# Spec Delta

## Purpose

Keeps one stored record per michi-no-eki station, using the data on its official page at michi-no-eki.jp. Scraping, search, and display all read and write this record.

## ADDED Requirements

### Requirement: Station identity
Each station SHALL have its own UUID, assigned by the system and independent of the official site. The numeric id in its official URL `https://www.michi-no-eki.jp/stations/views/{id}` SHALL be stored as its required source id. There SHALL be at most one station per source id.

#### Scenario: Own id assigned, source id kept
- **WHEN** a station is stored from `https://www.michi-no-eki.jp/stations/views/19949`
- **THEN** its source id is `19949` and its id is a system-assigned UUID, not taken from the URL

#### Scenario: Duplicate source id is rejected
- **GIVEN** a station with source id `19949` is stored
- **WHEN** another station with source id `19949` is inserted
- **THEN** the insert fails and only one station with that source id exists

### Requirement: Required station fields
Every station record SHALL have a name and a prefecture. The name excludes the `道の駅「…」` wrapper. Values stay in the original Japanese.

#### Scenario: Name and prefecture are stored
- **WHEN** the station from page 19949 is stored
- **THEN** its name is `ながおか花火館` and its prefecture is `新潟県`

#### Scenario: Missing name is rejected
- **WHEN** a record without a name is stored
- **THEN** it is rejected

### Requirement: English translations
A station record SHALL hold optional English versions of its name, prefecture, description, address, parking, and opening hours, stored next to the Japanese values. The English values SHALL never replace the Japanese ones.

#### Scenario: Untranslated station
- **WHEN** the station from page 19949 is stored without translations
- **THEN** its English name, prefecture, description, address, parking, and opening hours are null, and its Japanese values are stored as usual

#### Scenario: Translation stored alongside Japanese
- **GIVEN** the station from page 19949 is stored
- **WHEN** its English name `Nagaoka Hanabi-kan` and English prefecture `Niigata` are saved
- **THEN** both read back as saved, and its name is still `ながおか花火館` and its prefecture is still `新潟県`

### Requirement: Optional detail fields
A station record SHALL hold these optional fields: description, postal code, address, location (a geographic point), phone number, parking, opening hours, and map code. A field that is blank on the official page SHALL be stored as empty (null), not as an empty string.

#### Scenario: Location is split into postal code, address, and a point
- **WHEN** the station from page 19949 is stored from `940-2121 新潟県長岡市喜多町707番地` and map position `37.455106,138.80447`
- **THEN** its postal code is `940-2121`, its address is `新潟県長岡市喜多町707番地`, and its location reads back as latitude `37.455106` and longitude `138.80447`

#### Scenario: Blank map code is stored as null
- **WHEN** a station whose page shows an empty マップコード is stored
- **THEN** its map code is null

#### Scenario: Parking and hours are kept as shown
- **WHEN** the station from page 19949 is stored
- **THEN** its parking is `大型：18台　普通車：264台` and its phone number is `0258-86-7766`

### Requirement: Nearby lookup
Stations SHALL be findable by distance: given a point and a radius in metres, the lookup returns every stored station whose location is within that radius. Stations without a location SHALL never match.

#### Scenario: Station within radius is found
- **GIVEN** the station from page 19949 is stored at latitude `37.455106`, longitude `138.80447`
- **WHEN** stations within 1000 m of latitude `37.4551`, longitude `138.8045` are looked up
- **THEN** that station is returned

#### Scenario: Station outside radius is not found
- **GIVEN** the station from page 19949 is stored at its location
- **WHEN** stations within 1000 m of Tokyo Station (latitude `35.6812`, longitude `139.7671`) are looked up
- **THEN** that station is not returned

#### Scenario: Station without location never matches
- **GIVEN** a stored station with no location
- **WHEN** any nearby lookup runs
- **THEN** that station is not returned

### Requirement: Facilities
A station record SHALL list the facilities that are available, using the stable English codes for the site's 18 facility types. Facilities shown as unavailable SHALL be left out. Codes outside the 18 types SHALL be rejected.

#### Scenario: Only available facilities are listed
- **WHEN** the station from page 19949 is stored with ATM shown as unavailable and レストラン and EV充電施設 shown as available
- **THEN** its facilities include `restaurant` and `ev_charging` but not `atm`

#### Scenario: Unknown facility code is rejected
- **WHEN** a station is stored with the facility code `helipad`
- **THEN** it is rejected

#### Scenario: Station can be found by facility
- **GIVEN** stored stations with and without `ev_charging`
- **WHEN** stations are looked up by the facility `ev_charging`
- **THEN** only the stations that list `ev_charging` are returned

### Requirement: Images and websites
A station record SHALL hold an ordered list of image URLs and an ordered list of website URLs, both in page order. Either list MAY be empty.

#### Scenario: Image order is preserved
- **WHEN** the station from page 19949 is stored with its 3 gallery images
- **THEN** its images are the same 3 URLs, in gallery order

#### Scenario: Multiple websites are kept
- **WHEN** the station from page 19949 is stored with ホームページ and ホームページ2
- **THEN** its websites are `https://nagaoka-hanabikan.niigata.jp/` and then `https://www.instagram.com/nagaoka_hanabikan/`

#### Scenario: Station without images
- **WHEN** a station whose page has no gallery is stored
- **THEN** its images list is empty

### Requirement: Last updated time
Each station record SHALL record when it was last written.

#### Scenario: Timestamp set on write
- **WHEN** a station is inserted or updated
- **THEN** its last-updated time is the time of that write
