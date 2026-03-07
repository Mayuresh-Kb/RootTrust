# RootTrust Marketplace - Frontend

React + TypeScript frontend for the RootTrust AI-powered marketplace platform.

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM
- **HTTP Client**: Axios
- **AWS SDK**: @aws-sdk/client-s3 (for direct S3 uploads)

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── auth/           # Authentication components
│   ├── shared/         # Shared components (ProductCard, ImageUploader, etc.)
│   ├── consumer/       # Consumer-specific components
│   └── farmer/         # Farmer-specific components
├── pages/              # Page components
│   ├── consumer/       # Consumer portal pages
│   └── farmer/         # Farmer portal pages
├── contexts/           # React contexts (AuthContext, etc.)
├── services/           # API service layer
├── types/              # TypeScript type definitions
├── App.tsx             # Main app component
└── main.tsx            # Entry point
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Update the following variables:

- `VITE_API_BASE_URL`: Your API Gateway URL
- `VITE_AWS_REGION`: AWS region for S3 uploads
- `VITE_S3_BUCKET`: S3 bucket name for assets
- `VITE_RAZORPAY_KEY_ID`: Razorpay key for payments (optional)

### Development

```bash
# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Features

### Consumer Portal

- Browse seasonal marketplace with filters
- Search products by keyword
- View product details with AI authenticity scores
- Purchase products with integrated payment
- Leave reviews and ratings
- Share referral links
- Track orders

### Farmer Portal

- Upload products with images and documentation
- AI-powered fraud detection and verification
- AI-generated marketing content
- Create promotions and limited releases
- View analytics dashboard
- Track bonuses and incentives

## Key Components

### Authentication

- `AuthContext`: Global authentication state management
- `LoginForm`: User login component
- `RegistrationForm`: User registration component
- `ProtectedRoute`: Route guard for authenticated pages

### Shared Components

- `ProductCard`: Reusable product display card
- `ImageUploader`: S3 direct upload component
- `NotificationCenter`: Notification preferences management
- `ValueEquationDisplay`: Value proposition display
- `ScarcityIndicators`: Urgency and scarcity indicators
- `GIBadge`: Geographical Indication badge

### API Service Layer

- Centralized API client with Axios
- JWT token management
- Request/response interceptors
- Type-safe API methods

## Environment Variables

| Variable               | Description          | Default                 |
| ---------------------- | -------------------- | ----------------------- |
| `VITE_API_BASE_URL`    | Backend API endpoint | `http://localhost:3000` |
| `VITE_AWS_REGION`      | AWS region           | `us-east-1`             |
| `VITE_S3_BUCKET`       | S3 bucket for assets | `roottrust-assets-dev`  |
| `VITE_RAZORPAY_KEY_ID` | Razorpay payment key | -                       |

## Deployment

### AWS Amplify

1. Connect your Git repository to AWS Amplify
2. Configure build settings:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - cd frontend
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: frontend/dist
       files:
         - "**/*"
     cache:
       paths:
         - frontend/node_modules/**/*
   ```
3. Set environment variables in Amplify console
4. Deploy

### Manual Deployment

```bash
# Build the app
npm run build

# Deploy dist/ folder to your hosting service
```

## Testing

```bash
# Run unit tests (to be implemented)
npm run test

# Run tests in watch mode
npm run test:watch
```

## Code Style

- ESLint configuration included
- TypeScript strict mode enabled
- Tailwind CSS for styling

## Contributing

1. Follow the existing code structure
2. Use TypeScript for type safety
3. Follow React best practices
4. Use Tailwind CSS for styling
5. Keep components small and focused

## License

MIT
