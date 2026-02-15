# Requirements Document: RootTrust

## Executive Summary

RootTrust is an AI-powered agricultural intelligence platform designed to address critical challenges faced by small and marginal farmers in India: price unpredictability, middleman exploitation, and authenticity fraud in regional produce labeling. The platform provides three integrated capabilities: direct farmer-to-consumer discovery (without marketplace transactions), GPS-based Geographical Indication (GI) verification, and AI-driven predictive price intelligence.

The MVP targets one Indian state, supporting 5-7 major crops with a web-based interface. By combining transparent farmer profiles, location-verified authenticity badges, and data-backed price forecasts, RootTrust empowers farmers with actionable intelligence while building consumer trust in regional produce authenticity.

## Problem Statement

Small and marginal farmers (1-5 acres) face systemic challenges that reduce their income and market access:

1. **Price Unpredictability**: Farmers rely on past trends, hearsay, or middleman quotes to estimate crop prices 2-3 months before harvest. This leads to poor crop selection decisions and vulnerability to price crashes.

2. **Middleman Exploitation**: Opaque supply chains with multiple intermediaries reduce farmer margins by 30-50%. Farmers lack direct access to end consumers and transparent price information.

3. **Authenticity Fraud**: Fake regional labeling (GI misuse) allows non-authentic produce to claim premium prices. Genuine farmers producing GI-eligible crops lose premium value due to consumer distrust.

4. **Information Asymmetry**: Urban consumers seeking verified seasonal produce lack reliable channels to discover and contact authentic regional farmers.

These problems result in reduced farmer income, market inefficiency, and erosion of trust in regional agricultural brands.

## Objectives

RootTrust aims to achieve the following measurable objectives within the MVP phase:

1. **Transparency**: Enable direct farmer-consumer discovery with 100% GPS-verified farm locations and contact information for registered farmers.

2. **Authenticity**: Provide automated GI verification for eligible farms, reducing fake regional labeling by validating GPS location, crop-region consistency, and seasonal compatibility.

3. **Price Intelligence**: Deliver 2-3 month price forecasts with quantified confidence levels (target: 70%+ accuracy on MAE within ±15% of actual prices) to reduce farmer price uncertainty.

4. **Farmer Adoption**: Onboard 50+ farmers across 5-7 major crops in the target state during the pilot phase.

5. **Consumer Trust**: Achieve 80%+ consumer confidence in GI-verified produce badges through transparent validation criteria.

## Stakeholders

### Primary Stakeholders

- **Small/Marginal Farmers**: Users who register farms, add crop details, and access price intelligence
- **Urban Consumers**: Users who discover farms, verify authenticity, and contact farmers directly
- **Platform Administrators**: Manage crop database, GI mappings, and system configuration

### Secondary Stakeholders

- **Agricultural Extension Officers**: Potential users for farmer onboarding support
- **GI Registry Authorities**: Source of official GI boundary data
- **Mandi Boards**: Providers of historical price data

### Tertiary Stakeholders

- **Hackathon Judges**: Evaluators of technical merit and social impact
- **Potential Investors**: Future stakeholders for platform scaling

## User Personas

### Persona 1: Ramesh Kumar - Small Farmer

**Demographics**:

- Age: 42
- Location: Rural village in target state
- Farm size: 2.5 acres
- Crops: Seasonal vegetables and regional specialty crop
- Education: 10th standard
- Tech literacy: Basic smartphone usage

**Goals**:

- Understand fair price range before planting decisions
- Connect directly with consumers to avoid middleman margins
- Get recognition for authentic regional produce
- Reduce price uncertainty and income volatility

**Pain Points**:

- Cannot predict prices 2-3 months ahead
- Loses 40% margin to middlemen
- Consumers doubt authenticity of his GI-eligible crop
- No direct channel to reach urban buyers

**Usage Scenario**:
Ramesh registers his farm with GPS location, uploads photos of his land and crops, and adds harvest window details. He checks the AI price forecast for his specialty crop, which predicts ₹22-₹25/kg with 82% confidence and rising trend. Based on this, he decides to plant 1 acre of the crop. He receives direct inquiries from 3 urban consumers who verify his GI badge and contact him via phone.

### Persona 2: Priya Sharma - Urban Consumer

**Demographics**:

- Age: 34
- Location: Metropolitan city in target state
- Occupation: Software professional
- Income: Upper middle class
- Tech literacy: High

**Goals**:

- Source authentic regional produce directly from farmers
- Verify geographical authenticity of specialty crops
- Support small farmers by eliminating middlemen
- Access seasonal produce at fair prices

**Pain Points**:

- Cannot verify if "regional specialty" labels in markets are genuine
- No direct access to farmers producing authentic crops
- Willing to pay premium for verified produce but lacks trust
- Uncertain about fair price ranges

**Usage Scenario**:
Priya searches for a specific GI-registered regional crop on RootTrust. She filters by "GI-Verified" badge and views 5 nearby farms. She checks farm photos, GPS location on map, and sees the crop is in-season. The platform shows predicted price range of ₹22-₹25/kg. She contacts Ramesh directly via phone, negotiates ₹24/kg, and arranges pickup during harvest window.

## Glossary

- **GI (Geographical Indication)**: Legal certification that a product originates from a specific region with unique qualities attributable to that geography
- **Mandi**: Government-regulated agricultural wholesale market in India
- **MAE (Mean Absolute Error)**: Average absolute difference between predicted and actual prices
- **RMSE (Root Mean Square Error)**: Square root of average squared differences between predicted and actual prices
- **Harvest Window**: Time period when a crop is ready for harvest
- **Price Band**: Range of predicted prices (minimum to maximum)
- **Confidence Score**: Statistical measure of forecast reliability (0-100%)
- **Risk Indicator**: Classification of price volatility risk (Low/Medium/High)
- **Farm Profile**: Farmer-created page with location, crops, photos, and contact details
- **Verification Engine**: System component that validates GI eligibility
- **AI Engine**: System component that generates price forecasts

## Functional Requirements

### Requirement 1: Farmer Registration and Profile Management

**User Story**: As a farmer, I want to register my farm with verified location and crop details, so that consumers can discover and contact me directly.

#### Acceptance Criteria

1. WHEN a farmer registers, THE System SHALL capture GPS coordinates of the farm location
2. WHEN a farmer adds crop details, THE System SHALL validate crop name against the supported crop database
3. WHEN a farmer uploads farm photos, THE System SHALL accept JPEG/PNG formats up to 5MB per image
4. THE System SHALL store farmer contact information (phone number and optional email)
5. WHEN a farmer specifies harvest window, THE System SHALL validate date ranges are in the future
6. THE System SHALL allow farmers to mark crops as "available" or "sold out"
7. WHEN a farmer updates profile information, THE System SHALL timestamp the modification

### Requirement 2: Consumer Discovery and Search

**User Story**: As a consumer, I want to discover nearby farms growing specific crops, so that I can source authentic produce directly.

#### Acceptance Criteria

1. WHEN a consumer searches by crop name, THE System SHALL return all farms growing that crop within the target state
2. WHEN a consumer applies location filter, THE System SHALL calculate distance from consumer location to farm GPS coordinates
3. WHEN a consumer filters by "GI-Verified" badge, THE System SHALL return only farms that passed GI verification
4. WHEN displaying search results, THE System SHALL show farm name, crop, distance, harvest window, and verification status
5. THE System SHALL display farm location on an interactive map with GPS markers
6. WHEN a consumer views farm details, THE System SHALL display all uploaded photos, crop list, and contact information
7. WHEN a consumer requests contact, THE System SHALL reveal farmer phone number without intermediation

### Requirement 3: GI-Based Authenticity Verification

**User Story**: As a farmer growing GI-eligible crops, I want my produce to be automatically verified, so that consumers trust its authenticity and I can command premium prices.

#### Acceptance Criteria

1. WHEN a farmer registers a farm with GPS coordinates, THE Verification_Engine SHALL check if coordinates fall within any registered GI region boundaries
2. WHEN a farmer adds a crop, THE Verification_Engine SHALL validate if the crop matches the GI region's registered products
3. WHEN validating seasonal compatibility, THE Verification_Engine SHALL check if current month falls within the crop's growing season for that region
4. IF farm location, crop type, and season all match GI criteria, THEN THE System SHALL award "GI-Verified Produce" badge
5. IF any GI criterion fails, THEN THE System SHALL display the farm without verification badge
6. THE System SHALL display verification criteria (location match, crop match, season match) to consumers for transparency
7. WHEN GI boundaries or crop mappings are updated, THE System SHALL re-verify all affected farms within 24 hours

### Requirement 4: AI-Powered Price Forecasting

**User Story**: As a farmer, I want to see predicted prices for my crops 2-3 months ahead, so that I can make informed planting decisions and reduce income uncertainty.

#### Acceptance Criteria

1. WHEN a farmer views a crop, THE AI_Engine SHALL generate a price forecast for 2-3 months ahead
2. THE AI_Engine SHALL display predicted price as a range (minimum to maximum in ₹/kg)
3. THE AI_Engine SHALL display trend direction (Rising, Stable, Falling)
4. THE AI_Engine SHALL display confidence score as a percentage (0-100%)
5. THE AI_Engine SHALL display risk indicator (Low, Medium, High) based on historical price volatility
6. WHEN generating forecasts, THE AI_Engine SHALL use historical mandi prices, seasonal patterns, arrival volumes, and weather data as inputs
7. THE System SHALL display forecast generation timestamp and data sources used
8. THE System SHALL update forecasts weekly with latest available data
9. WHEN historical data is insufficient, THE System SHALL display "Insufficient Data" message instead of forecast

### Requirement 5: Price Intelligence Display

**User Story**: As a consumer, I want to see fair price ranges for crops, so that I can negotiate informed prices with farmers.

#### Acceptance Criteria

1. WHEN a consumer views a farm's crop, THE System SHALL display the same AI-generated price forecast shown to farmers
2. THE System SHALL display current mandi price range for comparison
3. THE System SHALL display historical price chart for the past 12 months
4. WHEN displaying price information, THE System SHALL include disclaimer: "Prices are predictions for guidance only. Final prices are negotiated between farmer and consumer."
5. THE System SHALL allow consumers to filter farms by predicted price range

### Requirement 6: Data Management and Administration

**User Story**: As a platform administrator, I want to manage crop database and GI mappings, so that the system remains accurate and up-to-date.

#### Acceptance Criteria

1. THE System SHALL provide admin interface to add, edit, and remove supported crops
2. THE System SHALL allow admins to upload GI region boundary data in GeoJSON format
3. THE System SHALL allow admins to map crops to GI regions with seasonal windows
4. WHEN admin updates GI mappings, THE System SHALL trigger re-verification of affected farms
5. THE System SHALL provide admin dashboard showing total farmers, crops, verified farms, and forecast accuracy metrics
6. THE System SHALL log all admin actions with timestamp and user ID

### Requirement 7: Data Input and Integration

**User Story**: As a system, I need to ingest historical price and weather data, so that the AI engine can generate accurate forecasts.

#### Acceptance Criteria

1. THE System SHALL accept historical mandi price data in CSV format with columns: date, crop, mandi_location, price_min, price_max, arrival_volume
2. THE System SHALL accept weather data in CSV format with columns: date, location, temperature, rainfall, humidity
3. WHEN ingesting data, THE System SHALL validate data types and reject malformed records
4. THE System SHALL store minimum 3 years of historical data for each supported crop
5. THE System SHALL update price data weekly from configured mandi data sources
6. IF data ingestion fails, THEN THE System SHALL log error details and alert administrators

### Requirement 8: User Authentication and Security

**User Story**: As a user, I want secure access to the platform, so that my data is protected.

#### Acceptance Criteria

1. WHEN a farmer registers, THE System SHALL require phone number verification via OTP
2. WHEN a user logs in, THE System SHALL authenticate using phone number and password
3. THE System SHALL enforce minimum password length of 8 characters
4. THE System SHALL hash passwords using bcrypt before storage
5. THE System SHALL implement session timeout after 24 hours of inactivity
6. THE System SHALL allow farmers to edit only their own farm profiles
7. WHEN a user requests password reset, THE System SHALL send OTP to registered phone number

### Requirement 9: Mobile Responsiveness

**User Story**: As a farmer with basic smartphone, I want the platform to work on mobile devices, so that I can access it from my farm.

#### Acceptance Criteria

1. THE System SHALL render all pages responsively on screen widths from 320px to 1920px
2. WHEN accessed on mobile, THE System SHALL display touch-friendly buttons with minimum 44px tap targets
3. THE System SHALL optimize images for mobile bandwidth (max 500KB per image on mobile)
4. WHEN capturing GPS location, THE System SHALL use device GPS on mobile browsers
5. THE System SHALL support both portrait and landscape orientations

### Requirement 10: Performance and Reliability

**User Story**: As a user in rural area with limited connectivity, I want the platform to load quickly and work reliably, so that I can access information without frustration.

#### Acceptance Criteria

1. WHEN a user loads the homepage, THE System SHALL render initial content within 3 seconds on 3G connection
2. WHEN a user searches for farms, THE System SHALL return results within 2 seconds for up to 1000 farms
3. WHEN the AI engine generates a forecast, THE System SHALL complete computation within 5 seconds
4. THE System SHALL maintain 99% uptime during business hours (6 AM - 10 PM IST)
5. WHEN the database is unavailable, THE System SHALL display cached data with staleness indicator
6. THE System SHALL handle concurrent access by 100 users without performance degradation

## Non-Functional Requirements

### Performance

1. THE System SHALL support 100 concurrent users during MVP phase
2. THE System SHALL scale to 1000 concurrent users within 6 months post-MVP
3. THE System SHALL process farm search queries in under 2 seconds for datasets up to 10,000 farms
4. THE AI_Engine SHALL generate price forecasts in under 5 seconds per crop
5. THE System SHALL optimize database queries to use indexes for location-based searches

### Scalability

1. THE System SHALL use horizontal scaling architecture to support multi-state expansion
2. THE System SHALL partition data by state to enable geographic scaling
3. THE System SHALL support addition of new crops without code changes (configuration-driven)
4. THE System SHALL support addition of new GI regions via admin interface without deployment

### Reliability

1. THE System SHALL implement automated database backups every 24 hours
2. THE System SHALL log all errors with stack traces for debugging
3. THE System SHALL implement retry logic for external API calls (weather data, mandi prices)
4. THE System SHALL validate all user inputs to prevent data corruption
5. THE System SHALL implement graceful degradation when AI forecasts are unavailable

### Security

1. THE System SHALL encrypt all data in transit using TLS 1.2 or higher
2. THE System SHALL encrypt sensitive data at rest (passwords, phone numbers)
3. THE System SHALL implement rate limiting (100 requests per minute per IP) to prevent abuse
4. THE System SHALL sanitize all user inputs to prevent SQL injection and XSS attacks
5. THE System SHALL implement CORS policies to restrict API access to authorized domains
6. THE System SHALL not store payment information (out of scope for MVP)

### Explainability

1. THE System SHALL display all input features used in price forecasts (historical prices, weather, seasonality)
2. THE System SHALL display confidence scores and risk indicators with forecasts
3. THE System SHALL explain GI verification criteria (location, crop, season) for transparency
4. THE System SHALL provide data source attribution for all displayed information
5. THE System SHALL include disclaimers that forecasts are guidance, not guarantees

### Usability

1. THE System SHALL support English and one regional language (target state's primary language)
2. THE System SHALL use simple language suitable for users with 10th standard education
3. THE System SHALL provide inline help text for all form fields
4. THE System SHALL display error messages in user-friendly language with corrective actions
5. THE System SHALL use consistent navigation patterns across all pages

### Maintainability

1. THE System SHALL use modular architecture with clear separation between frontend, backend, AI engine, and verification engine
2. THE System SHALL document all APIs using OpenAPI specification
3. THE System SHALL implement comprehensive logging for debugging
4. THE System SHALL use version control for all code and configuration
5. THE System SHALL implement automated testing for critical paths (registration, search, verification, forecasting)

## Success Metrics

### Adoption Metrics

- **Farmer Registration**: 50+ farmers registered within 3 months of launch
- **Consumer Registration**: 200+ consumers registered within 3 months of launch
- **Active Usage**: 60% of registered farmers log in at least once per month
- **Direct Connections**: 100+ farmer-consumer connections facilitated within 3 months

### Technical Metrics

- **Forecast Accuracy**: MAE within ±15% of actual prices for 70%+ of forecasts
- **GI Verification Rate**: 30%+ of registered farms achieve GI-Verified badge
- **System Uptime**: 99%+ uptime during business hours
- **Response Time**: 95% of page loads complete within 3 seconds

### Impact Metrics

- **Price Transparency**: 80%+ of farmers report improved price awareness (survey)
- **Consumer Trust**: 80%+ of consumers trust GI-verified badges (survey)
- **Farmer Income**: 20%+ increase in farmer margins through direct sales (survey, 6-month follow-up)

### Engagement Metrics

- **Profile Completeness**: 80%+ of farmer profiles have photos and complete crop details
- **Search Activity**: Average 5+ farm searches per consumer per session
- **Forecast Usage**: 70%+ of farmers view price forecasts before planting decisions

## Scope & Limitations

### In Scope (MVP)

1. **Geographic Coverage**: One Indian state only
2. **Crop Coverage**: 5-7 major crops (to be selected based on data availability)
3. **User Types**: Farmers and consumers only (no admin marketplace features)
4. **Functionality**: Discovery, verification, price intelligence (no transactions, logistics, or payments)
5. **Platform**: Web-based responsive application (no native mobile apps)
6. **Data Sources**: Historical mandi prices, weather data, static GI mappings
7. **Forecasting**: 2-3 month short-term forecasts only
8. **Language**: English and one regional language

### Out of Scope (MVP)

1. **Transactions**: No payment gateway, escrow, or transaction processing
2. **Logistics**: No delivery, transportation, or fulfillment services
3. **Marketplace**: No bidding, auctions, or price enforcement
4. **Bulk Pooling**: No farmer cooperative or bulk aggregation features
5. **IoT Integration**: No soil sensors, weather stations, or farm automation
6. **Real-time Pricing**: No live mandi price feeds (weekly updates only)
7. **Multi-state**: No support for multiple states in MVP
8. **Native Apps**: No iOS or Android native applications
9. **Advanced Analytics**: No yield prediction, disease detection, or crop recommendations
10. **Social Features**: No farmer forums, reviews, or ratings

### Future Enhancements (Post-MVP)

1. Multi-state expansion with state-specific crop databases
2. Integration with payment gateways for optional transaction support
3. Logistics partner integration for delivery coordination
4. Native mobile applications for iOS and Android
5. Real-time mandi price feeds and alerts
6. Farmer cooperative and bulk pooling features
7. Yield prediction and crop recommendation models
8. IoT sensor integration for real-time farm monitoring
9. Blockchain-based traceability for supply chain transparency
10. Multi-language support for pan-India expansion

## Assumptions

### Technical Assumptions

1. **Data Availability**: Historical mandi price data for target crops is available for minimum 3 years
2. **GI Data**: Official GI region boundary data is available in digital format (GeoJSON or shapefile)
3. **Weather Data**: Historical weather data is available from public APIs or government sources
4. **GPS Accuracy**: Smartphone GPS provides accuracy within 10-50 meters for farm location
5. **Internet Connectivity**: Target users have access to 3G or better mobile internet

### User Assumptions

1. **Farmer Tech Literacy**: Farmers can operate basic smartphone functions (camera, GPS, form filling)
2. **Phone Ownership**: Target farmers own smartphones with GPS capability
3. **Language**: Farmers and consumers can read English or the regional language
4. **Trust**: Farmers are willing to share farm location and contact information publicly
5. **Negotiation**: Farmers and consumers are comfortable negotiating prices directly

### Business Assumptions

1. **No Transaction Fees**: Platform does not charge transaction fees (sustainability model TBD)
2. **Voluntary Adoption**: Farmers and consumers adopt platform voluntarily without incentives
3. **Data Quality**: Mandi price data is reasonably accurate and representative
4. **GI Compliance**: Farmers understand GI criteria and do not intentionally misrepresent location
5. **Legal Compliance**: Platform complies with agricultural marketing regulations in target state

### Operational Assumptions

1. **Manual Onboarding**: Initial farmer onboarding may require field support from extension officers
2. **Data Updates**: Mandi price data can be updated weekly (not real-time)
3. **Verification Accuracy**: GPS-based GI verification is sufficient for MVP (no field audits)
4. **Support**: Basic customer support via phone/email is sufficient for MVP
5. **Hosting**: Cloud hosting (AWS/GCP/Azure) is available and affordable for MVP scale

## Constraints

### Technical Constraints

1. **Budget**: Limited hackathon/MVP budget restricts infrastructure and third-party services
2. **Timeline**: MVP must be developed within hackathon timeline or 3-month post-hackathon period
3. **Team Size**: Small development team (2-4 developers)
4. **Data Access**: Dependent on availability and quality of public data sources
5. **Mobile Compatibility**: Must work on low-end Android devices with limited RAM

### Regulatory Constraints

1. **Agricultural Marketing**: Must comply with state agricultural marketing regulations
2. **Data Privacy**: Must comply with Indian data protection laws for user information
3. **GI Regulations**: Cannot issue official GI certifications (only informational badges)
4. **Consumer Protection**: Must include disclaimers that platform does not guarantee transactions

### User Constraints

1. **Digital Literacy**: Must accommodate users with limited tech experience
2. **Language Barriers**: Must support regional language for accessibility
3. **Connectivity**: Must function on slow 3G connections in rural areas
4. **Device Limitations**: Must work on devices with small screens and limited processing power

## Dependencies

### External Dependencies

1. **Mandi Price Data**: Dependent on government mandi boards or Agmarknet for historical data
2. **Weather Data**: Dependent on IMD (India Meteorological Department) or third-party weather APIs
3. **GI Registry**: Dependent on official GI registry for region boundary data
4. **Map Services**: Dependent on Google Maps API or OpenStreetMap for location display
5. **SMS Gateway**: Dependent on third-party SMS service for OTP verification

### Internal Dependencies

1. **AI Model Training**: Forecast accuracy depends on quality of historical data and model training
2. **GI Mapping**: Verification accuracy depends on completeness of GI region database
3. **User Adoption**: Platform value depends on critical mass of farmers and consumers
4. **Data Quality**: Forecast reliability depends on accuracy of input data sources

## Risks

### Technical Risks

1. **Data Quality**: Poor quality mandi data may reduce forecast accuracy
   - Mitigation: Validate data sources, implement data quality checks, use multiple sources

2. **GPS Inaccuracy**: GPS errors may cause incorrect GI verification
   - Mitigation: Set tolerance thresholds, allow manual location correction, display verification criteria

3. **Scalability**: Platform may not scale beyond MVP without architecture changes
   - Mitigation: Design with scalability in mind, use cloud services, implement caching

### Adoption Risks

1. **Farmer Reluctance**: Farmers may not trust digital platforms or share location
   - Mitigation: Partner with extension officers, provide training, demonstrate value

2. **Low Consumer Demand**: Insufficient consumer interest in direct sourcing
   - Mitigation: Target urban consumers interested in organic/authentic produce, marketing campaigns

3. **Network Effects**: Platform requires critical mass of both farmers and consumers
   - Mitigation: Focus on specific crops with strong demand, geographic clustering

### Operational Risks

1. **Data Maintenance**: Keeping GI mappings and crop data current requires ongoing effort
   - Mitigation: Design admin tools for easy updates, automate data refresh where possible

2. **Support Burden**: High support requests from low-literacy users
   - Mitigation: Invest in UX design, provide comprehensive help documentation, video tutorials

3. **Misuse**: Users may provide false information or misuse contact details
   - Mitigation: Implement reporting mechanisms, phone verification, community moderation

## Glossary Addendum

- **Agmarknet**: Government of India portal providing agricultural marketing information
- **IMD**: India Meteorological Department, official weather data provider
- **OTP**: One-Time Password for phone number verification
- **GeoJSON**: Geographic data format for representing region boundaries
- **Bcrypt**: Cryptographic hashing algorithm for password security
- **CORS**: Cross-Origin Resource Sharing, web security mechanism
- **TLS**: Transport Layer Security, encryption protocol for data in transit
- **MAE**: Mean Absolute Error, forecast accuracy metric
- **RMSE**: Root Mean Square Error, forecast accuracy metric
- **MVP**: Minimum Viable Product, initial version with core features
