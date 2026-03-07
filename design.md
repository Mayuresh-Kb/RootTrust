# Design Document: RootTrust

## System Overview

RootTrust is a three-tier web application that connects farmers directly with consumers while providing AI-powered price intelligence and GPS-based authenticity verification. The system architecture separates concerns into distinct layers: presentation (web frontend), application logic (backend API), intelligence engines (AI forecasting and GI verification), and data persistence (relational database).

The platform operates as an information and discovery service, not a transactional marketplace. Farmers create profiles with GPS-verified locations, crop details, and contact information. Consumers search for farms, view authenticity badges, access price forecasts, and contact farmers directly. The AI engine generates 2-3 month price forecasts using historical mandi data, weather patterns, and seasonal trends. The verification engine validates GI eligibility by cross-referencing farm GPS coordinates with official GI region boundaries and crop-season compatibility rules.

### Key Design Principles

1. **Transparency**: All verification criteria and forecast inputs are visible to users
2. **Simplicity**: Clean interfaces suitable for users with basic digital literacy
3. **Modularity**: Independent components (AI, verification, backend) for maintainability
4. **Scalability**: Stateless services and database partitioning for geographic expansion
5. **Reliability**: Graceful degradation when external data sources are unavailable
6. **Security**: Defense-in-depth with input validation, authentication, and encryption

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Frontend                             │
│              (React/Vue.js - Responsive SPA)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Farmer  │  │ Consumer │  │   Admin  │  │   Maps   │       │
│  │   UI     │  │    UI    │  │    UI    │  │ Display  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST API
┌────────────────────────┴────────────────────────────────────────┐
│                      Backend API Layer                           │
│                  (Node.js/Python - Express/FastAPI)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Auth   │  │  Farmer  │  │ Consumer │  │  Admin   │       │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└────────┬───────────────┬───────────────┬────────────────────────┘
         │               │               │
    ┌────┴────┐     ┌────┴────┐    ┌────┴────┐
    │   AI    │     │   GI    │    │Database │
    │ Engine  │     │Verifier │    │ (Postgres│
    │(Python) │     │(Python) │    │ +PostGIS)│
    └────┬────┘     └────┬────┘    └────┬────┘
         │               │               │
    ┌────┴────────┐ ┌────┴────────┐    │
    │  ML Model   │ │ GI Registry │    │
    │  (Trained)  │ │  (GeoJSON)  │    │
    └─────────────┘ └─────────────┘    │
         │                              │
    ┌────┴──────────────────────────────┴────┐
    │      External Data Sources              │
    │  ┌──────────┐  ┌──────────┐           │
    │  │  Mandi   │  │ Weather  │           │
    │  │  Prices  │  │   Data   │           │
    │  └──────────┘  └──────────┘           │
    └─────────────────────────────────────────┘
```

### Technology Stack Justification

**Frontend**: React or Vue.js for component-based UI development with responsive design. Leaflet.js or Google Maps API for interactive map display. Tailwind CSS for rapid, mobile-first styling.

**Backend**: Node.js with Express or Python with FastAPI. Python preferred for seamless integration with AI/ML libraries. RESTful API design for clear separation of concerns.

**AI Engine**: Python with scikit-learn or statsmodels for time series forecasting. Libraries chosen for simplicity and interpretability over deep learning complexity (limited data, need for explainability).

**Database**: PostgreSQL with PostGIS extension for geospatial queries (GI boundary checks, distance calculations). Relational model for data integrity and complex queries.

**Deployment**: Docker containers for consistent environments. Cloud hosting (AWS/GCP/Azure) with managed database services. CI/CD pipeline for automated testing and deployment.

## Component-Level Architecture

### Frontend Components

**Farmer Dashboard**

- Registration form with GPS capture (browser geolocation API)
- Profile management (crop CRUD, photo upload, harvest window)
- Price forecast viewer with charts and trend indicators
- Contact request notifications

**Consumer Interface**

- Crop search with filters (location, GI-verified, price range)
- Interactive map with farm markers (clustered for performance)
- Farm detail view (photos, crops, verification status, contact)
- Price intelligence display (forecast, historical chart, mandi comparison)

**Admin Panel**

- Crop database management (add/edit/remove crops)
- GI region upload (GeoJSON import, crop-region mapping)
- System dashboard (metrics: users, farms, forecasts, accuracy)
- Data ingestion tools (mandi prices, weather data)

**Shared Components**

- Authentication (login, registration, OTP verification)
- Navigation (responsive header, mobile menu)
- Map display (Leaflet with custom markers)
- Charts (price trends using Chart.js or D3.js)

### Backend Services

**Authentication Service**

- User registration with phone OTP verification
- Login with JWT token generation
- Password hashing (bcrypt) and validation
- Session management and token refresh
- Role-based access control (farmer, consumer, admin)

**Farmer Service**

- Farm profile CRUD operations
- Photo upload to cloud storage (S3/Cloud Storage)
- GPS coordinate validation and storage
- Crop association and harvest window management
- Profile search and filtering

**Consumer Service**

- Farm search with geospatial queries
- Distance calculation from consumer location
- Filter application (GI-verified, crop type, availability)
- Contact information retrieval

**Admin Service**

- Crop database management
- GI region data import and validation
- System metrics aggregation
- Data ingestion orchestration

**Integration Layer**

- External API clients (weather, mandi prices)
- Retry logic and circuit breakers for resilience
- Data transformation and normalization
- Caching for frequently accessed data

### AI Engine

**Purpose**: Generate 2-3 month price forecasts with confidence scores and risk indicators.

**Components**:

1. **Data Preprocessor**
   - Loads historical mandi prices, weather data, arrival volumes
   - Handles missing values (forward fill, interpolation)
   - Creates time-based features (month, season, year)
   - Normalizes price data by crop and region

2. **Feature Engineer**
   - Lag features (prices from 1, 2, 3 months ago)
   - Rolling statistics (7-day, 30-day moving averages)
   - Seasonal indicators (binary flags for growing/harvest seasons)
   - Weather aggregates (average temperature, total rainfall for month)
   - Arrival volume trends (increasing/decreasing)

3. **Forecasting Model**
   - Algorithm: SARIMA (Seasonal AutoRegressive Integrated Moving Average) or Random Forest Regressor
   - SARIMA chosen for interpretability and effectiveness with seasonal data
   - Random Forest as alternative for handling non-linear relationships
   - Separate model trained per crop (crop-specific patterns)
   - Training data: 3 years of historical prices minimum

4. **Prediction Generator**
   - Generates point forecasts for 2-3 months ahead
   - Calculates prediction intervals (80% confidence) for price range
   - Computes confidence score based on model's historical accuracy
   - Determines trend direction (rising/stable/falling) from forecast slope

5. **Risk Classifier**
   - Calculates historical price volatility (standard deviation)
   - Classifies risk: Low (<15% volatility), Medium (15-30%), High (>30%)
   - Considers forecast uncertainty in risk assessment

**Model Training Pipeline**:

- Offline training on historical data (weekly refresh)
- Cross-validation for hyperparameter tuning
- Performance evaluation (MAE, RMSE, MAPE)
- Model versioning and A/B testing capability

**Inference Pipeline**:

- Real-time prediction on API request
- Caching of forecasts (24-hour TTL)
- Fallback to last known forecast if model unavailable

### Verification Engine

**Purpose**: Validate GI eligibility based on GPS location, crop type, and seasonality.

**Components**:

1. **GI Registry Loader**
   - Parses GeoJSON files with GI region boundaries
   - Stores polygons in PostGIS geometry columns
   - Maintains crop-to-region mappings with seasonal windows
   - Example: "Darjeeling Tea" → Darjeeling district polygon + April-November season

2. **Location Validator**
   - Receives farm GPS coordinates (latitude, longitude)
   - Performs point-in-polygon query using PostGIS ST_Contains
   - Returns matching GI regions (farm may be in multiple regions)
   - Handles edge cases (coordinates on boundary, invalid coordinates)

3. **Crop Matcher**
   - Receives crop name from farm profile
   - Queries GI registry for crops registered in matched regions
   - Returns boolean: crop is/isn't registered for that region
   - Example: "Basmati Rice" in Punjab region → match

4. **Season Validator**
   - Receives current date and crop name
   - Queries seasonal window for crop in that region
   - Returns boolean: current month is/isn't in growing season
   - Example: Checking "Alphonso Mango" in April → match (season: March-June)

5. **Badge Generator**
   - Combines results from location, crop, and season validators
   - Awards "GI-Verified Produce" badge if all three match
   - Stores verification status and criteria details
   - Generates human-readable explanation for transparency

**Verification Logic**:

```
IF (farm_location IN gi_region_boundary) AND
   (farm_crop IN gi_region_crops) AND
   (current_month IN crop_season_window)
THEN
   award_gi_verified_badge = TRUE
ELSE
   award_gi_verified_badge = FALSE
```

**Re-verification Triggers**:

- Farm location updated
- Crop added/removed from farm
- GI region boundaries updated by admin
- Seasonal window changes (monthly cron job)

### Database Schema

**Users Table**

- `id` (UUID, primary key)
- `phone` (string, unique, indexed)
- `password_hash` (string)
- `role` (enum: farmer, consumer, admin)
- `created_at`, `updated_at` (timestamps)

**Farms Table**

- `id` (UUID, primary key)
- `user_id` (UUID, foreign key to Users)
- `name` (string)
- `location` (PostGIS geography point, indexed)
- `address` (string)
- `photos` (array of URLs)
- `created_at`, `updated_at` (timestamps)

**Crops Table**

- `id` (UUID, primary key)
- `name` (string, unique)
- `category` (string: vegetable, fruit, grain, spice)
- `season_start_month` (integer 1-12)
- `season_end_month` (integer 1-12)
- `created_at`, `updated_at` (timestamps)

**FarmCrops Table** (many-to-many)

- `id` (UUID, primary key)
- `farm_id` (UUID, foreign key to Farms)
- `crop_id` (UUID, foreign key to Crops)
- `harvest_start_date` (date)
- `harvest_end_date` (date)
- `availability_status` (enum: available, sold_out)
- `gi_verified` (boolean)
- `verification_details` (JSON: location_match, crop_match, season_match)
- `created_at`, `updated_at` (timestamps)

**GIRegions Table**

- `id` (UUID, primary key)
- `name` (string, unique)
- `boundary` (PostGIS geometry polygon, indexed)
- `state` (string)
- `registered_crops` (array of crop IDs)
- `created_at`, `updated_at` (timestamps)

**PriceData Table**

- `id` (UUID, primary key)
- `crop_id` (UUID, foreign key to Crops)
- `date` (date, indexed)
- `mandi_location` (string)
- `price_min` (decimal)
- `price_max` (decimal)
- `arrival_volume` (decimal, kg)
- `source` (string: agmarknet, manual)
- `created_at` (timestamp)

**WeatherData Table**

- `id` (UUID, primary key)
- `date` (date, indexed)
- `location` (string)
- `temperature_avg` (decimal, Celsius)
- `rainfall` (decimal, mm)
- `humidity` (decimal, percentage)
- `source` (string: IMD, openweather)
- `created_at` (timestamp)

**Forecasts Table**

- `id` (UUID, primary key)
- `crop_id` (UUID, foreign key to Crops)
- `forecast_date` (date, indexed)
- `target_month` (date)
- `price_min` (decimal)
- `price_max` (decimal)
- `trend` (enum: rising, stable, falling)
- `confidence_score` (decimal 0-100)
- `risk_indicator` (enum: low, medium, high)
- `model_version` (string)
- `created_at` (timestamp)

**Indexes**:

- `Farms.location` (spatial index for geospatial queries)
- `GIRegions.boundary` (spatial index)
- `PriceData.crop_id, date` (composite index for time series queries)
- `Forecasts.crop_id, forecast_date` (composite index)
- `Users.phone` (unique index for authentication)

## Data Flow

### Flow 1: Farmer Registration and GI Verification

1. **User Action**: Farmer opens registration page, fills form (name, phone, password)
2. **Frontend**: Captures GPS coordinates using browser geolocation API
3. **Frontend**: Sends POST request to `/api/auth/register` with user data and GPS
4. **Backend Auth Service**:
   - Validates input (phone format, password strength)
   - Generates OTP and sends via SMS gateway
   - Stores temporary registration data in cache (Redis)
5. **User Action**: Enters OTP received on phone
6. **Backend Auth Service**:
   - Validates OTP
   - Hashes password with bcrypt
   - Creates user record in Users table
   - Creates farm record in Farms table with GPS location
   - Returns JWT token
7. **User Action**: Adds crop to farm profile
8. **Backend Farmer Service**:
   - Validates crop exists in Crops table
   - Creates FarmCrops record
   - Triggers GI verification
9. **Verification Engine**:
   - Queries GIRegions table with ST_Contains(boundary, farm.location)
   - Checks if crop is in matched region's registered_crops
   - Checks if current month is in crop's seasonal window
   - Updates FarmCrops.gi_verified and verification_details
10. **Backend**: Returns updated farm profile with GI badge status
11. **Frontend**: Displays profile with "GI-Verified Produce" badge if applicable

### Flow 2: Consumer Search and Discovery

1. **User Action**: Consumer enters crop name in search box
2. **Frontend**: Sends GET request to `/api/farms/search?crop=tomato&gi_verified=true&lat=28.6&lon=77.2&radius=50`
3. **Backend Consumer Service**:
   - Queries Farms table joined with FarmCrops and Crops
   - Applies filters: crop name match, gi_verified=true
   - Calculates distance using PostGIS ST_Distance(farm.location, consumer_location)
   - Filters by radius (50 km)
   - Orders by distance ascending
   - Limits to 50 results
4. **Backend**: Returns array of farm objects with distance, crops, verification status
5. **Frontend**: Displays results as list and map markers
6. **User Action**: Clicks on farm to view details
7. **Frontend**: Sends GET request to `/api/farms/{farm_id}`
8. **Backend Farmer Service**:
   - Queries Farms table with farm_id
   - Joins FarmCrops, Crops, Users tables
   - Returns complete farm profile
9. **Frontend**: Displays farm photos, crops, location map, contact button
10. **User Action**: Clicks "View Contact"
11. **Frontend**: Reveals farmer phone number (no backend call needed)

### Flow 3: Price Forecast Generation

1. **User Action**: Farmer views crop in their profile
2. **Frontend**: Sends GET request to `/api/forecasts/{crop_id}`
3. **Backend**: Checks Forecasts table for recent forecast (< 24 hours old)
4. **If cached forecast exists**:
   - Returns cached forecast from database
5. **If no cached forecast**:
   - Backend calls AI Engine `/predict` endpoint with crop_id
6. **AI Engine**:
   - Loads trained model for crop from disk
   - Queries PriceData table for historical prices (last 3 years)
   - Queries WeatherData table for historical weather
   - Preprocesses data (handle missing values, create features)
   - Generates features (lags, rolling averages, seasonal indicators)
   - Runs model.predict() for 2-3 months ahead
   - Calculates prediction intervals (80% confidence)
   - Computes confidence score from model's historical MAE
   - Determines trend direction from forecast slope
   - Classifies risk based on historical volatility
7. **AI Engine**: Returns forecast object (price_min, price_max, trend, confidence, risk)
8. **Backend**: Stores forecast in Forecasts table with 24-hour TTL
9. **Backend**: Returns forecast to frontend
10. **Frontend**: Displays forecast with chart, trend arrow, confidence badge, risk indicator

### Flow 4: Admin GI Region Update

1. **User Action**: Admin uploads GeoJSON file with new GI region
2. **Frontend**: Sends POST request to `/api/admin/gi-regions` with file
3. **Backend Admin Service**:
   - Validates GeoJSON format
   - Parses polygons and metadata
   - Inserts record into GIRegions table with PostGIS geometry
4. **User Action**: Admin maps crops to region
5. **Backend Admin Service**:
   - Updates GIRegions.registered_crops array
   - Triggers re-verification job
6. **Background Job**:
   - Queries all FarmCrops records
   - For each record, calls Verification Engine
   - Updates gi_verified status
7. **Backend**: Returns success message with count of re-verified farms

### Flow 5: Weekly Data Ingestion

1. **Cron Job**: Triggers weekly at Sunday midnight
2. **Backend Integration Layer**:
   - Calls external mandi price API (Agmarknet)
   - Fetches price data for all supported crops
   - Validates data format and completeness
   - Transforms to internal schema
   - Bulk inserts into PriceData table
3. **Backend Integration Layer**:
   - Calls weather API (IMD or OpenWeather)
   - Fetches historical weather for target state
   - Transforms to internal schema
   - Bulk inserts into WeatherData table
4. **Backend**: Triggers model retraining job
5. **AI Engine**:
   - Loads updated PriceData and WeatherData
   - Retrains models for all crops
   - Evaluates model performance (MAE, RMSE)
   - Saves new model versions to disk
   - Logs metrics to monitoring system
6. **Backend**: Invalidates all cached forecasts (forces regeneration)

## AI/ML Design

### Model Selection Justification

**Primary Choice: SARIMA (Seasonal AutoRegressive Integrated Moving Average)**

Rationale:

- Agricultural prices exhibit strong seasonal patterns (harvest cycles, festivals)
- SARIMA explicitly models seasonality with seasonal AR and MA terms
- Interpretable: coefficients show impact of past prices and seasonal effects
- Proven effectiveness for time series forecasting with limited data
- Lower computational cost than deep learning (important for real-time inference)
- Provides prediction intervals naturally (uncertainty quantification)

**Alternative: Random Forest Regressor**

Rationale:

- Handles non-linear relationships between features (weather, arrival volumes)
- Robust to outliers and missing data
- Feature importance scores aid explainability
- Can incorporate exogenous variables easily (weather, festivals)
- Ensemble method reduces overfitting

**Decision**: Start with SARIMA for simplicity and interpretability. Evaluate Random Forest if SARIMA accuracy is insufficient (<70% forecasts within ±15% MAE).

### Feature Engineering

**Temporal Features**:

- `month` (1-12): Captures seasonal patterns
- `quarter` (1-4): Broader seasonal grouping
- `year`: Captures long-term trends
- `day_of_year` (1-365): Fine-grained seasonality

**Lag Features** (past prices):

- `price_lag_1`: Price 1 month ago
- `price_lag_2`: Price 2 months ago
- `price_lag_3`: Price 3 months ago
- `price_lag_12`: Price 12 months ago (year-over-year)

**Rolling Statistics**:

- `price_ma_7`: 7-day moving average (smooths noise)
- `price_ma_30`: 30-day moving average (trend)
- `price_std_30`: 30-day rolling standard deviation (volatility)

**Seasonal Indicators**:

- `is_harvest_season`: Binary flag (1 if current month in harvest window)
- `is_sowing_season`: Binary flag (1 if current month in sowing window)
- `months_to_harvest`: Integer (months until next harvest)

**Weather Features**:

- `temp_avg_30`: Average temperature over past 30 days
- `rainfall_total_30`: Total rainfall over past 30 days
- `rainfall_deviation`: Difference from historical average (drought/flood indicator)

**Market Features**:

- `arrival_volume`: Quantity arriving at mandi (supply indicator)
- `arrival_trend`: Percentage change in arrivals vs. previous month
- `price_volatility`: Standard deviation of prices over past 90 days

**Derived Features**:

- `price_change_pct`: Percentage change from previous month
- `season_price_ratio`: Current price / average price for this season
- `supply_demand_ratio`: Arrival volume / historical average (proxy for supply pressure)

### Model Training Process

**Data Preparation**:

1. Load 3 years of historical data from PriceData and WeatherData tables
2. Merge datasets on date and location
3. Handle missing values:
   - Forward fill for prices (carry last known price)
   - Interpolate for weather (linear interpolation)
   - Drop rows with >20% missing features
4. Create train/test split: 80% train (first 2.4 years), 20% test (last 0.6 years)

**SARIMA Configuration**:

- Order (p, d, q): AutoRegressive, Differencing, Moving Average terms
- Seasonal order (P, D, Q, s): Seasonal AR, Differencing, MA, and period
- Use auto_arima (pmdarima library) to find optimal hyperparameters
- Seasonal period s=12 (monthly data with yearly seasonality)

**Random Forest Configuration** (if used):

- n_estimators: 100 trees
- max_depth: 10 (prevent overfitting)
- min_samples_split: 20 (require sufficient data per split)
- Use GridSearchCV for hyperparameter tuning

**Training Loop**:

```python
for crop in supported_crops:
    # Load crop-specific data
    data = load_price_data(crop, years=3)

    # Feature engineering
    features = engineer_features(data)

    # Train-test split
    X_train, X_test, y_train, y_test = split_data(features)

    # Train model
    model = SARIMA(order=(1,1,1), seasonal_order=(1,1,1,12))
    model.fit(y_train)

    # Evaluate
    predictions = model.predict(len(y_test))
    mae = mean_absolute_error(y_test, predictions)
    rmse = sqrt(mean_squared_error(y_test, predictions))

    # Save model
    save_model(model, crop, version=timestamp)
    log_metrics(crop, mae, rmse)
```

### Evaluation Metrics

**Mean Absolute Error (MAE)**:

- Formula: `MAE = (1/n) * Σ|actual - predicted|`
- Interpretation: Average rupees difference between forecast and actual price
- Target: MAE < 15% of average crop price
- Example: If average price is ₹20/kg, target MAE < ₹3/kg

**Root Mean Square Error (RMSE)**:

- Formula: `RMSE = sqrt((1/n) * Σ(actual - predicted)²)`
- Interpretation: Penalizes large errors more than MAE
- Target: RMSE < 20% of average crop price
- Used to detect systematic bias or outliers

**Mean Absolute Percentage Error (MAPE)**:

- Formula: `MAPE = (1/n) * Σ|(actual - predicted) / actual| * 100`
- Interpretation: Average percentage error
- Target: MAPE < 15%
- Useful for comparing accuracy across crops with different price scales

**Forecast Accuracy Rate**:

- Percentage of forecasts where actual price falls within predicted range
- Target: 70%+ of forecasts have actual price within [price_min, price_max]
- Directly measures user-facing accuracy

**Directional Accuracy**:

- Percentage of forecasts where trend direction (rising/falling) matches reality
- Target: 75%+ directional accuracy
- Important for planting decisions (farmers care about trend)

### Confidence Score Calculation

Confidence score represents forecast reliability based on model's historical performance:

```python
def calculate_confidence(model, crop):
    # Get historical MAE for this crop
    historical_mae = get_historical_mae(crop)

    # Get average price for this crop
    avg_price = get_average_price(crop)

    # Calculate percentage error
    pct_error = (historical_mae / avg_price) * 100

    # Convert to confidence score (inverse relationship)
    # 0% error = 100% confidence, 30% error = 0% confidence
    confidence = max(0, 100 - (pct_error * 3.33))

    return round(confidence, 0)
```

Example:

- Historical MAE = ₹2/kg, Average price = ₹20/kg
- Percentage error = 10%
- Confidence = 100 - (10 \* 3.33) = 67%

### Risk Classification Logic

Risk indicator classifies price volatility to help farmers assess uncertainty:

```python
def classify_risk(crop, forecast_range):
    # Calculate historical volatility
    historical_prices = get_historical_prices(crop, months=12)
    volatility = std_dev(historical_prices) / mean(historical_prices) * 100

    # Calculate forecast range width
    range_width = (forecast_range.max - forecast_range.min) / forecast_range.min * 100

    # Combine historical and forecast volatility
    combined_volatility = (volatility + range_width) / 2

    # Classify
    if combined_volatility < 15:
        return "Low"
    elif combined_volatility < 30:
        return "Medium"
    else:
        return "High"
```

Risk Interpretation:

- **Low**: Stable prices, low uncertainty, safe planting decision
- **Medium**: Moderate fluctuations, some uncertainty, diversify crops
- **High**: High volatility, significant uncertainty, risky planting decision

## GI Verification Logic

The GI verification system validates farm authenticity through three independent checks that must all pass:

### Algorithm Overview

```
function verify_gi_eligibility(farm, crop):
    # Step 1: Location Check
    matching_regions = []
    for gi_region in gi_regions_database:
        if point_in_polygon(farm.gps_coordinates, gi_region.boundary):
            matching_regions.append(gi_region)

    if len(matching_regions) == 0:
        return {verified: false, reason: "location_outside_gi_regions"}

    # Step 2: Crop Check
    crop_matches = false
    for region in matching_regions:
        if crop.id in region.registered_crops:
            crop_matches = true
            matched_region = region
            break

    if not crop_matches:
        return {verified: false, reason: "crop_not_registered_for_region"}

    # Step 3: Season Check
    current_month = get_current_month()
    crop_season = get_crop_season(crop, matched_region)

    if current_month in range(crop_season.start_month, crop_season.end_month):
        season_matches = true
    else:
        season_matches = false

    if not season_matches:
        return {verified: false, reason: "outside_growing_season"}

    # All checks passed
    return {
        verified: true,
        region: matched_region.name,
        criteria: {
            location_match: true,
            crop_match: true,
            season_match: true
        }
    }
```

### Point-in-Polygon Implementation

Uses PostGIS ST_Contains function for geometric validation:

```sql
SELECT gi_regions.id, gi_regions.name
FROM gi_regions
WHERE ST_Contains(
    gi_regions.boundary,
    ST_SetSRID(ST_MakePoint(farm_longitude, farm_latitude), 4326)
);
```

- SRID 4326: WGS84 coordinate system (standard GPS)
- Returns all GI regions containing the farm point
- Handles edge cases: point on boundary returns true (inclusive)

### Seasonal Window Matching

Handles wrap-around seasons (e.g., November to March):

```python
def is_in_season(current_month, season_start, season_end):
    if season_start <= season_end:
        # Normal season (e.g., March to June)
        return season_start <= current_month <= season_end
    else:
        # Wrap-around season (e.g., November to March)
        return current_month >= season_start or current_month <= season_end
```

### Verification Transparency

All verification results include detailed criteria for user transparency:

```json
{
  "gi_verified": true,
  "verification_details": {
    "location_match": true,
    "matched_region": "Darjeeling",
    "crop_match": true,
    "registered_crop": "Tea",
    "season_match": true,
    "current_month": "April",
    "growing_season": "April-November"
  },
  "verified_at": "2024-01-15T10:30:00Z"
}
```

## API Design Overview

### Authentication Endpoints

**POST /api/auth/register**

- Request: `{phone, password, name, farm_name, gps_lat, gps_lon}`
- Response: `{user_id, token, message: "OTP sent"}`
- Generates OTP, stores in cache

**POST /api/auth/verify-otp**

- Request: `{phone, otp}`
- Response: `{user_id, token, farm_id}`
- Creates user and farm records

**POST /api/auth/login**

- Request: `{phone, password}`
- Response: `{user_id, token, role}`
- Returns JWT token (24-hour expiry)

**POST /api/auth/reset-password**

- Request: `{phone}`
- Response: `{message: "OTP sent"}`
- Sends OTP for password reset

### Farmer Endpoints

**GET /api/farms/my-profile**

- Headers: `Authorization: Bearer {token}`
- Response: `{farm_id, name, location, crops[], photos[]}`
- Returns authenticated farmer's profile

**PUT /api/farms/my-profile**

- Headers: `Authorization: Bearer {token}`
- Request: `{name?, address?, photos[]?}`
- Response: `{farm_id, updated_at}`
- Updates farm profile

**POST /api/farms/crops**

- Headers: `Authorization: Bearer {token}`
- Request: `{crop_id, harvest_start, harvest_end}`
- Response: `{farm_crop_id, gi_verified, verification_details}`
- Adds crop to farm, triggers GI verification

**PUT /api/farms/crops/{farm_crop_id}/status**

- Headers: `Authorization: Bearer {token}`
- Request: `{status: "available" | "sold_out"}`
- Response: `{farm_crop_id, status, updated_at}`
- Updates crop availability

### Consumer Endpoints

**GET /api/farms/search**

- Query params: `crop_id?, gi_verified?, lat?, lon?, radius_km?, limit?`
- Response: `{farms: [{farm_id, name, distance_km, crops[], gi_verified}], total}`
- Returns paginated search results

**GET /api/farms/{farm_id}**

- Response: `{farm_id, name, location, crops[], photos[], contact, verification_details}`
- Returns complete farm profile

**GET /api/crops**

- Query params: `category?, search?`
- Response: `{crops: [{crop_id, name, category, season}]}`
- Returns list of supported crops

### Forecast Endpoints

**GET /api/forecasts/{crop_id}**

- Response: `{crop_id, forecast_date, target_month, price_min, price_max, trend, confidence, risk, sources[]}`
- Returns cached or generates new forecast

**GET /api/forecasts/{crop_id}/historical**

- Query params: `months?` (default: 12)
- Response: `{crop_id, data: [{date, price_min, price_max, arrival_volume}]}`
- Returns historical price data for charts

### Admin Endpoints

**POST /api/admin/crops**

- Headers: `Authorization: Bearer {admin_token}`
- Request: `{name, category, season_start_month, season_end_month}`
- Response: `{crop_id, created_at}`
- Adds new crop to database

**POST /api/admin/gi-regions**

- Headers: `Authorization: Bearer {admin_token}`
- Request: `{name, state, boundary_geojson, registered_crop_ids[]}`
- Response: `{gi_region_id, created_at}`
- Imports GI region with boundary

**POST /api/admin/data/ingest-prices**

- Headers: `Authorization: Bearer {admin_token}`
- Request: CSV file upload
- Response: `{records_imported, records_rejected, errors[]}`
- Ingests mandi price data

**GET /api/admin/dashboard**

- Headers: `Authorization: Bearer {admin_token}`
- Response: `{total_farmers, total_consumers, total_farms, gi_verified_farms, forecast_accuracy_mae}`
- Returns system metrics

### Error Response Format

All endpoints return consistent error format:

```json
{
  "error": {
    "code": "INVALID_CROP",
    "message": "Crop ID does not exist in database",
    "details": {
      "crop_id": "invalid-uuid"
    }
  }
}
```

HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad request (validation error)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (insufficient permissions)
- 404: Not found
- 500: Internal server error

## Deployment Strategy

### Infrastructure

**Cloud Provider**: AWS (alternative: GCP or Azure)

**Compute**:

- Frontend: S3 + CloudFront (static hosting with CDN)
- Backend API: ECS Fargate (containerized, auto-scaling)
- AI Engine: Lambda functions (on-demand inference) or ECS for persistent service
- Background Jobs: Lambda (scheduled via EventBridge)

**Database**:

- RDS PostgreSQL with PostGIS extension
- Multi-AZ deployment for high availability
- Automated backups (daily snapshots, 7-day retention)
- Read replicas for scaling read-heavy queries

**Storage**:

- S3 for farm photos (with CloudFront CDN)
- S3 for trained ML models
- ElastiCache Redis for session storage and forecast caching

**Networking**:

- VPC with public and private subnets
- Application Load Balancer for backend API
- Security groups restricting database access to backend only

### CI/CD Pipeline

**Source Control**: GitHub

**Build Pipeline** (GitHub Actions):

1. Code push triggers workflow
2. Run linters (ESLint, Pylint)
3. Run unit tests and property tests
4. Build Docker images for backend and AI engine
5. Push images to ECR (Elastic Container Registry)
6. Build frontend static assets
7. Run integration tests against staging environment

**Deployment Pipeline**:

1. Staging deployment (automatic on main branch)
2. Run smoke tests on staging
3. Manual approval gate for production
4. Blue-green deployment to production
5. Health checks and rollback on failure

### Environment Configuration

**Development**:

- Local Docker Compose setup
- SQLite or local PostgreSQL
- Mock external APIs (mandi, weather)
- Hot reload for rapid development

**Staging**:

- Mirrors production architecture
- Separate database with anonymized data
- Real external API integrations
- Used for QA and demo

**Production**:

- Full infrastructure as described above
- Monitoring and alerting enabled
- Automated backups and disaster recovery
- Rate limiting and DDoS protection

### Monitoring and Observability

**Application Monitoring**:

- CloudWatch for logs aggregation
- Custom metrics: API latency, error rates, forecast accuracy
- Alarms for high error rates, slow responses, database connection issues

**Infrastructure Monitoring**:

- CloudWatch for CPU, memory, disk usage
- RDS performance insights for database queries
- Auto-scaling triggers based on CPU and request count

**User Analytics**:

- Google Analytics for user behavior
- Custom events: searches, farm views, contact requests
- Conversion funnel: registration → profile completion → contact

**Error Tracking**:

- Sentry for exception tracking and stack traces
- Grouped by error type and frequency
- Alerts for new or recurring errors

### Security Measures

**Network Security**:

- HTTPS only (TLS 1.2+)
- WAF (Web Application Firewall) for DDoS protection
- Rate limiting (100 req/min per IP)
- CORS policies restricting API access

**Data Security**:

- Encryption at rest (RDS, S3)
- Encryption in transit (TLS)
- Password hashing (bcrypt, cost factor 12)
- Secrets management (AWS Secrets Manager)

**Access Control**:

- IAM roles with least privilege
- JWT tokens with short expiry (24 hours)
- Role-based access control (farmer, consumer, admin)
- Audit logs for admin actions

**Compliance**:

- GDPR-compliant data handling (user consent, data deletion)
- Indian data protection laws compliance
- Regular security audits and penetration testing

## Technical Risks & Mitigation

### Risk 1: Poor Forecast Accuracy

**Impact**: Users lose trust, platform value diminishes

**Mitigation**:

- Set realistic expectations (70% accuracy target, not 100%)
- Display confidence scores and risk indicators prominently
- Include disclaimers that forecasts are guidance, not guarantees
- Continuously monitor MAE and retrain models weekly
- Implement A/B testing for model improvements
- Collect user feedback on forecast usefulness

### Risk 2: Insufficient Historical Data

**Impact**: Cannot train accurate models for some crops

**Mitigation**:

- Start with 5-7 major crops with good data availability
- Partner with government mandi boards for data access
- Display "Insufficient Data" message for unsupported crops
- Gradually expand crop coverage as data accumulates
- Use transfer learning from similar crops if applicable

### Risk 3: GPS Inaccuracy

**Impact**: Incorrect GI verification, user frustration

**Mitigation**:

- Set tolerance threshold (e.g., 50m buffer around GI boundaries)
- Allow manual location correction with map interface
- Display verification criteria transparently
- Implement admin review for disputed verifications
- Use multiple GPS readings and average for accuracy

### Risk 4: Low User Adoption

**Impact**: Network effects don't materialize, platform fails

**Mitigation**:

- Partner with agricultural extension officers for farmer onboarding
- Provide training and support in regional language
- Target specific crops with strong consumer demand
- Focus on geographic clusters (one district initially)
- Offer incentives for early adopters (featured listings)
- Demonstrate value through case studies and testimonials

### Risk 5: Scalability Bottlenecks

**Impact**: Performance degrades as users grow

**Mitigation**:

- Design stateless services for horizontal scaling
- Implement caching aggressively (forecasts, search results)
- Use database indexes for geospatial queries
- Partition data by state for geographic scaling
- Load test before launch (simulate 1000 concurrent users)
- Monitor performance metrics and scale proactively

### Risk 6: External API Failures

**Impact**: Cannot update price data or weather data

**Mitigation**:

- Implement retry logic with exponential backoff
- Use circuit breakers to prevent cascading failures
- Cache last known data and serve with staleness indicator
- Have backup data sources (multiple mandi APIs)
- Graceful degradation (show historical data if forecast unavailable)
- Alert admins on repeated failures

### Risk 7: Data Quality Issues

**Impact**: Garbage in, garbage out for forecasts

**Mitigation**:

- Implement data validation on ingestion (type checks, range checks)
- Reject malformed records and log errors
- Monitor data freshness (alert if no updates for 7 days)
- Cross-validate with multiple sources
- Allow admins to manually correct data
- Display data source and timestamp for transparency

### Risk 8: Security Vulnerabilities

**Impact**: Data breaches, user trust loss, legal liability

**Mitigation**:

- Follow OWASP Top 10 security practices
- Input validation and sanitization on all endpoints
- Regular security audits and penetration testing
- Keep dependencies updated (automated vulnerability scanning)
- Implement rate limiting and DDoS protection
- Have incident response plan for breaches

## Future Scalability Plan

### Phase 1: MVP (Months 1-3)

- Single state, 5-7 crops
- 50+ farmers, 200+ consumers
- Basic features: discovery, verification, forecasting
- Manual data ingestion

### Phase 2: State Expansion (Months 4-6)

- Add 2-3 more states
- 10-15 crops per state
- 500+ farmers, 2000+ consumers
- Automated data ingestion pipelines
- Mobile-optimized web app

### Phase 3: Feature Enhancement (Months 7-12)

- Native mobile apps (iOS, Android)
- Real-time mandi price feeds
- Push notifications for price alerts
- Farmer cooperative features (bulk pooling)
- Integration with logistics partners
- Multi-language support (5+ languages)

### Phase 4: Advanced Intelligence (Year 2)

- Yield prediction models
- Crop recommendation system
- Disease detection (image recognition)
- Weather-based risk alerts
- Blockchain traceability
- IoT sensor integration

### Scaling Architecture

**Database Sharding**:

- Partition by state (each state gets own database)
- Cross-state queries use federated approach
- Reduces single database bottleneck

**Microservices**:

- Split monolithic backend into services:
  - Auth Service
  - Farm Service
  - Forecast Service
  - Verification Service
  - Search Service
- Independent scaling and deployment

**CDN and Caching**:

- CloudFront for global content delivery
- Redis cluster for distributed caching
- Cache forecasts, search results, farm profiles
- Reduce database load by 80%+

**Async Processing**:

- Message queue (SQS) for background jobs
- Decouple verification, forecast generation from API requests
- Improve API response times

**Multi-Region Deployment**:

- Deploy in multiple AWS regions (Mumbai, Delhi)
- Route users to nearest region (latency optimization)
- Cross-region replication for disaster recovery

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, I identified the following redundancies and consolidations:

**Redundancy Analysis**:

- Properties 1.4 and 1.6 (contact info storage and crop status storage) are both round-trip properties that can be generalized into a single "data persistence" property
- Properties 2.4 and 2.6 (search result completeness and detail view completeness) both test data completeness and can be combined
- Properties 4.2, 4.3, 4.4, 4.5 (forecast field validations) are all invariants about forecast structure that can be combined into one comprehensive property
- Properties 3.4 and 3.5 (GI badge award and non-award) are logical inverses that can be tested as a single property

**Consolidated Properties**:
The following properties represent the minimal set needed for comprehensive validation, with redundancies eliminated.

### Registration and Profile Properties

**Property 1: GPS Capture on Registration**
_For any_ farmer registration, the system should capture and store GPS coordinates, and those coordinates should be retrievable from the farm profile.
**Validates: Requirements 1.1**

**Property 2: Crop Validation**
_For any_ crop name input, the system should accept it if and only if it exists in the supported crop database.
**Validates: Requirements 1.2**

**Property 3: Photo Upload Validation**
_For any_ uploaded file, the system should accept it if and only if it is JPEG or PNG format and size is ≤ 5MB.
**Validates: Requirements 1.3**

**Property 4: Data Persistence Round-Trip**
_For any_ farmer profile data (contact info, crop status, harvest window), storing then retrieving should return equivalent data.
**Validates: Requirements 1.4, 1.6**

**Property 5: Future Date Validation**
_For any_ harvest window date range, the system should accept it if and only if both start and end dates are in the future.
**Validates: Requirements 1.5**

**Property 6: Update Timestamp Monotonicity**
_For any_ profile update, the new updated_at timestamp should be strictly greater than the previous updated_at timestamp.
**Validates: Requirements 1.7**

### Search and Discovery Properties

**Property 7: Search Completeness**
_For any_ crop name and set of farms, searching by that crop should return exactly the farms that have that crop in their FarmCrops records.
**Validates: Requirements 2.1**

**Property 8: Distance Calculation Accuracy**
_For any_ two GPS coordinate pairs, the calculated distance should match the Haversine formula result within 1% tolerance.
**Validates: Requirements 2.2**

**Property 9: GI Filter Correctness**
_For any_ search with gi_verified=true filter, all returned farms should have at least one crop with gi_verified=true.
**Validates: Requirements 2.3**

**Property 10: Response Data Completeness**
_For any_ farm in search results or detail view, the response should contain all required fields (name, crops, location, contact, verification status, photos).
**Validates: Requirements 2.4, 2.6**

**Property 11: Map Coordinate Consistency**
_For any_ farm displayed on map, the GPS coordinates passed to the map component should match the farm's stored location coordinates.
**Validates: Requirements 2.5**

**Property 12: Contact Information Access**
_For any_ farm, requesting contact details should return the farmer's stored phone number without modification.
**Validates: Requirements 2.7**

### GI Verification Properties

**Property 13: Point-in-Polygon Accuracy**
_For any_ GPS coordinates and GI region polygon, the point-in-polygon check should correctly determine containment using PostGIS ST_Contains.
**Validates: Requirements 3.1**

**Property 14: Crop-Region Membership**
_For any_ crop and GI region, the crop should be considered registered if and only if the crop ID is in the region's registered_crops array.
**Validates: Requirements 3.2**

**Property 15: Seasonal Window Validation**
_For any_ month and crop seasonal window, the month should be considered in-season if it falls within [season_start_month, season_end_month], handling wrap-around seasons correctly.
**Validates: Requirements 3.3**

**Property 16: GI Badge Logic Completeness**
_For any_ farm and crop combination, the GI-Verified badge should be awarded if and only if all three conditions are true: (1) farm location is within a GI region boundary, (2) crop is registered for that region, and (3) current month is within the crop's growing season.
**Validates: Requirements 3.4, 3.5**

**Property 17: Verification Transparency**
_For any_ farm crop, the verification_details field should contain boolean values for location_match, crop_match, and season_match.
**Validates: Requirements 3.6**

### Price Forecasting Properties

**Property 18: Forecast Generation**
_For any_ crop with at least 3 years of historical price data, the AI engine should generate a forecast containing all required fields.
**Validates: Requirements 4.1**

**Property 19: Forecast Structure Invariants**
_For any_ generated forecast, the following invariants must hold: (1) price_min ≤ price_max, (2) trend ∈ {Rising, Stable, Falling}, (3) 0 ≤ confidence_score ≤ 100, (4) risk_indicator ∈ {Low, Medium, High}, (5) forecast contains timestamp and sources.
**Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.7**

**Property 20: Forecast Consistency Across Users**
_For any_ crop and time period, the forecast returned to farmers should be identical to the forecast returned to consumers.
**Validates: Requirements 5.1**

**Property 21: Historical Data Completeness**
_For any_ crop with available data, the historical price response should contain data points spanning up to 12 months, with each point containing date, price_min, price_max, and arrival_volume.
**Validates: Requirements 5.3**

**Property 22: Price Range Filter Correctness**
_For any_ price range filter [min_price, max_price], all returned farms should have crops with forecasts where price_min ≥ min_price AND price_max ≤ max_price.
**Validates: Requirements 5.5**

### Admin and Data Management Properties

**Property 23: Crop CRUD Round-Trip**
_For any_ crop data, creating a crop then retrieving it should return equivalent crop data (name, category, season).
**Validates: Requirements 6.1**

**Property 24: GeoJSON Parsing Round-Trip**
_For any_ valid GeoJSON polygon, uploading it then querying the stored geometry should return an equivalent polygon (within floating-point precision).
**Validates: Requirements 6.2**

**Property 25: Crop-Region Mapping Persistence**
_For any_ crop-to-region mapping with seasonal window, storing then retrieving should return the same mapping.
**Validates: Requirements 6.3**

**Property 26: Dashboard Metrics Accuracy**
_For any_ system state, the dashboard metrics (total_farmers, total_farms, gi_verified_farms) should match the actual database counts from respective tables.
**Validates: Requirements 6.5**

**Property 27: Admin Action Audit Trail**
_For any_ admin action (crop creation, GI region upload, data ingestion), a log entry should be created containing timestamp, user_id, action_type, and details.
**Validates: Requirements 6.6**

### Data Ingestion Properties

**Property 28: CSV Parsing Validation**
_For any_ CSV file with correct columns (date, crop, price_min, price_max, arrival_volume for mandi data; date, location, temperature, rainfall, humidity for weather data), the system should parse it successfully and reject files with missing or incorrect columns.
**Validates: Requirements 7.1, 7.2**

**Property 29: Malformed Record Rejection**
_For any_ data record with invalid data types (e.g., non-numeric price, invalid date format), the system should reject the record and not store it in the database.
**Validates: Requirements 7.3**

**Property 30: Historical Data Retention**
_For any_ supported crop, querying historical price data should return at least 3 years of data (or all available data if less than 3 years have been collected).
**Validates: Requirements 7.4**

**Property 31: Ingestion Error Logging**
_For any_ data ingestion failure (parse error, validation error, database error), an error log entry should be created with error details and timestamp.
**Validates: Requirements 7.6**

### Authentication and Security Properties

**Property 32: OTP Verification Workflow**
_For any_ registration attempt, an OTP should be generated and sent, and registration should complete if and only if the correct OTP is provided within the validity window.
**Validates: Requirements 8.1**

**Property 33: Authentication Logic**
_For any_ login attempt, authentication should succeed if and only if the phone number exists and the provided password matches the stored hash.
**Validates: Requirements 8.2**

**Property 34: Password Length Enforcement**
_For any_ password input during registration, the system should reject it if length < 8 characters.
**Validates: Requirements 8.3**

**Property 35: Password Hashing Security**
_For any_ stored user password, the password field should contain a bcrypt hash (starting with "$2b$" or "$2a$"), never plaintext.
**Validates: Requirements 8.4**

**Property 36: Authorization Boundary**
_For any_ farmer user, they should be able to edit their own farm profiles (user_id matches farm.user_id) but receive 403 Forbidden when attempting to edit other farmers' profiles.
**Validates: Requirements 8.6**

**Property 37: Password Reset OTP**
_For any_ password reset request with valid phone number, an OTP should be sent to that phone number.
**Validates: Requirements 8.7**

### Performance and Reliability Properties

**Property 38: Mobile Image Optimization**
_For any_ image served to mobile devices (detected by User-Agent or viewport width < 768px), the file size should be ≤ 500KB.
**Validates: Requirements 9.3**

**Property 39: Graceful Degradation**
_For any_ database unavailability scenario, the system should return cached data (if available) with a staleness indicator field (cached: true, cached_at: timestamp).
**Validates: Requirements 10.5**

### Edge Cases and Examples

**Example 1: Insufficient Data Handling**
When a crop has less than 3 years of historical data, the forecast endpoint should return status 200 with message "Insufficient data for reliable forecast" instead of generating a forecast.
**Validates: Requirements 4.9**

**Example 2: Price Disclaimer Presence**
When displaying any price information (forecast or historical), the response or UI should include the disclaimer text: "Prices are predictions for guidance only. Final prices are negotiated between farmer and consumer."
**Validates: Requirements 5.4**

## Error Handling

### Input Validation Errors

**Invalid GPS Coordinates**:

- Validation: Latitude ∈ [-90, 90], Longitude ∈ [-180, 180]
- Error: `{code: "INVALID_GPS", message: "GPS coordinates out of valid range"}`
- HTTP Status: 400

**Invalid Crop ID**:

- Validation: Crop ID exists in Crops table
- Error: `{code: "INVALID_CROP", message: "Crop ID does not exist"}`
- HTTP Status: 404

**Invalid Date Range**:

- Validation: harvest_start_date < harvest_end_date, both in future
- Error: `{code: "INVALID_DATE_RANGE", message: "Harvest dates must be in future and start before end"}`
- HTTP Status: 400

**Invalid File Upload**:

- Validation: File type ∈ {JPEG, PNG}, size ≤ 5MB
- Error: `{code: "INVALID_FILE", message: "File must be JPEG or PNG and under 5MB"}`
- HTTP Status: 400

### Authentication Errors

**Invalid OTP**:

- Validation: OTP matches generated code, not expired (5-minute window)
- Error: `{code: "INVALID_OTP", message: "OTP is incorrect or expired"}`
- HTTP Status: 401

**Invalid Credentials**:

- Validation: Phone exists, password matches hash
- Error: `{code: "INVALID_CREDENTIALS", message: "Phone or password is incorrect"}`
- HTTP Status: 401

**Expired Token**:

- Validation: JWT token not expired, signature valid
- Error: `{code: "TOKEN_EXPIRED", message: "Session expired, please login again"}`
- HTTP Status: 401

**Insufficient Permissions**:

- Validation: User role has permission for action
- Error: `{code: "FORBIDDEN", message: "You do not have permission for this action"}`
- HTTP Status: 403

### Data Processing Errors

**Forecast Generation Failure**:

- Cause: Model file missing, insufficient data, computation error
- Error: `{code: "FORECAST_UNAVAILABLE", message: "Unable to generate forecast at this time"}`
- HTTP Status: 503
- Fallback: Return last cached forecast with staleness indicator

**GI Verification Failure**:

- Cause: GI region data missing, PostGIS query error
- Error: `{code: "VERIFICATION_UNAVAILABLE", message: "Unable to verify GI eligibility"}`
- HTTP Status: 503
- Fallback: Set gi_verified=false, retry verification in background

**External API Failure**:

- Cause: Mandi API timeout, weather API rate limit
- Error: Logged internally, not exposed to user
- Fallback: Use cached data, display staleness indicator
- Retry: Exponential backoff (1s, 2s, 4s, 8s, 16s)

### Database Errors

**Connection Failure**:

- Cause: Database unreachable, connection pool exhausted
- Error: `{code: "SERVICE_UNAVAILABLE", message: "Service temporarily unavailable"}`
- HTTP Status: 503
- Fallback: Return cached data if available

**Query Timeout**:

- Cause: Slow query, database overload
- Error: `{code: "TIMEOUT", message: "Request timed out, please try again"}`
- HTTP Status: 504
- Mitigation: Query timeout set to 10 seconds, optimize with indexes

**Constraint Violation**:

- Cause: Duplicate phone number, foreign key violation
- Error: `{code: "DUPLICATE_ENTRY", message: "Phone number already registered"}`
- HTTP Status: 409

### Error Logging Strategy

All errors are logged with structured format:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "service": "backend-api",
  "endpoint": "/api/farms/crops",
  "method": "POST",
  "user_id": "uuid",
  "error_code": "INVALID_CROP",
  "error_message": "Crop ID does not exist",
  "stack_trace": "...",
  "request_id": "uuid"
}
```

Critical errors (database failures, external API failures) trigger alerts to administrators via email/SMS.

## Testing Strategy

RootTrust employs a dual testing approach combining unit tests for specific examples and edge cases with property-based tests for universal correctness guarantees.

### Unit Testing

Unit tests validate specific examples, integration points, and edge cases:

**Focus Areas**:

- Specific examples demonstrating correct behavior (e.g., "Darjeeling Tea" in Darjeeling region gets GI badge)
- Integration between components (e.g., API endpoint calls verification engine)
- Edge cases (e.g., GPS coordinates exactly on GI boundary, wrap-around seasons)
- Error conditions (e.g., invalid OTP, expired token, database unavailable)

**Example Unit Tests**:

- Test farmer registration with valid data succeeds
- Test farmer registration with duplicate phone fails
- Test GI verification for known GI crop in correct region
- Test GI verification fails when crop outside season
- Test forecast generation with insufficient data returns error
- Test search returns empty array when no farms match
- Test admin cannot edit farmer's profile (authorization)

**Balance**: Unit tests should focus on concrete scenarios and integration points. Avoid writing too many unit tests for input validation—property tests handle comprehensive input coverage.

### Property-Based Testing

Property tests validate universal properties across randomized inputs:

**Configuration**:

- Library: Hypothesis (Python), fast-check (JavaScript/TypeScript)
- Iterations: Minimum 100 per property test
- Shrinking: Enabled to find minimal failing examples
- Seed: Randomized but logged for reproducibility

**Tagging Convention**:
Each property test must include a comment tag referencing the design document:

```python
# Feature: root-trust, Property 2: Crop Validation
@given(crop_name=st.text())
def test_crop_validation(crop_name):
    # Test implementation
```

**Property Test Examples**:

```python
# Feature: root-trust, Property 8: Distance Calculation Accuracy
@given(
    lat1=st.floats(min_value=-90, max_value=90),
    lon1=st.floats(min_value=-180, max_value=180),
    lat2=st.floats(min_value=-90, max_value=90),
    lon2=st.floats(min_value=-180, max_value=180)
)
def test_distance_calculation_accuracy(lat1, lon1, lat2, lon2):
    calculated = calculate_distance(lat1, lon1, lat2, lon2)
    expected = haversine_formula(lat1, lon1, lat2, lon2)
    assert abs(calculated - expected) / expected < 0.01  # Within 1%
```

```python
# Feature: root-trust, Property 16: GI Badge Logic Completeness
@given(
    farm_location=st.tuples(
        st.floats(min_value=-90, max_value=90),
        st.floats(min_value=-180, max_value=180)
    ),
    crop_id=st.uuids(),
    current_month=st.integers(min_value=1, max_value=12)
)
def test_gi_badge_logic(farm_location, crop_id, current_month):
    location_match = check_location_in_gi_region(farm_location)
    crop_match = check_crop_registered(crop_id, location_match.region_id)
    season_match = check_season(current_month, crop_id)

    badge_awarded = verify_gi_eligibility(farm_location, crop_id, current_month)

    assert badge_awarded == (location_match and crop_match and season_match)
```

```python
# Feature: root-trust, Property 19: Forecast Structure Invariants
@given(crop_id=st.uuids())
def test_forecast_structure_invariants(crop_id):
    # Assume crop has sufficient data
    forecast = generate_forecast(crop_id)

    assert forecast.price_min <= forecast.price_max
    assert forecast.trend in ["Rising", "Stable", "Falling"]
    assert 0 <= forecast.confidence_score <= 100
    assert forecast.risk_indicator in ["Low", "Medium", "High"]
    assert forecast.timestamp is not None
    assert len(forecast.sources) > 0
```

```python
# Feature: root-trust, Property 4: Data Persistence Round-Trip
@given(
    phone=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',))),
    harvest_start=st.dates(min_value=date.today()),
    harvest_end=st.dates(min_value=date.today())
)
def test_data_persistence_round_trip(phone, harvest_start, harvest_end):
    # Create farmer with contact info
    farmer_id = create_farmer(phone=phone)

    # Retrieve farmer
    retrieved = get_farmer(farmer_id)

    assert retrieved.phone == phone

    # Add crop with harvest window
    crop_id = add_crop_to_farm(farmer_id, harvest_start, harvest_end)

    # Retrieve crop
    retrieved_crop = get_farm_crop(crop_id)

    assert retrieved_crop.harvest_start == harvest_start
    assert retrieved_crop.harvest_end == harvest_end
```

### Integration Testing

Integration tests validate end-to-end flows across multiple components:

**Test Scenarios**:

- Complete farmer registration flow (API → Auth Service → Database → Verification Engine)
- Complete consumer search flow (API → Search Service → Database → Distance Calculation)
- Complete forecast generation flow (API → AI Engine → Model → Database)
- GI verification trigger on crop addition (API → Farmer Service → Verification Engine → Database)
- Data ingestion flow (CSV Upload → Validation → Database → Model Retraining)

**Environment**: Staging environment with test database and mock external APIs

### Performance Testing

Load tests validate system performance under expected and peak loads:

**Tools**: Apache JMeter or Locust

**Scenarios**:

- 100 concurrent users (MVP target): Search, view farms, generate forecasts
- 1000 concurrent users (6-month target): Sustained load for 10 minutes
- Spike test: Sudden increase from 100 to 500 users

**Metrics**:

- Response time: 95th percentile < 2 seconds
- Error rate: < 1%
- Database connections: < 80% of pool size
- CPU usage: < 70%

### Acceptance Testing

Manual testing by stakeholders to validate user experience:

**Test Cases**:

- Farmer can register, add crops, view forecasts
- Consumer can search, filter, view farm details, get contact
- Admin can add crops, upload GI regions, view dashboard
- Mobile responsiveness on various devices
- Regional language display and input

**Acceptance Criteria**: All user stories from requirements document are demonstrable.
