import { Link } from "react-router-dom";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* HERO */}
      <div className="hero-gradient">
        <div className="container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center">
            {/* AI Badge */}
            <div className="inline-flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm mb-6">
              <svg
                className="w-4 h-4 text-primary"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M13 7H7v6h6V7z" />
                <path
                  fillRule="evenodd"
                  d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="text-sm font-semibold text-gray-700">
                AI-Powered Verification
              </span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-6 leading-tight">
              AI-Powered Marketplace
              <br />
              <span className="text-gradient">
                Connecting Farmers & Consumers
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg md:text-xl text-gray-600 mb-10 max-w-3xl mx-auto">
              Buy authentic GI-tagged agricultural products directly from
              verified farmers. Powered by Amazon Bedrock AI for fraud detection
              and authenticity verification.
            </p>

            {/* CTA */}
            <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
              <Link
                to="/consumer/dashboard"
                className="inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-700 text-white px-8 py-4 rounded-xl text-lg font-semibold shadow-md hover:shadow-lg transition"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
                  />
                </svg>
                Browse Products
              </Link>

              <Link
                to="/register"
                className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-primary border border-primary px-8 py-4 rounded-xl text-lg font-semibold shadow-md hover:shadow-lg transition"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M18 9v3m0 0v3m0-3h3m-3 0h-3"
                  />
                </svg>
                Register Now
              </Link>
            </div>

            {/* Trust Indicators */}
            <div className="flex flex-wrap justify-center gap-8 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="font-medium">AI-Verified Products</span>
              </div>

              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="font-medium">Direct from Farmers</span>
              </div>

              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="font-medium">Secure Transactions</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* FEATURES */}
      <div className="bg-white py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Why Choose RootTrust?
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Leveraging AI technology to ensure authenticity and build trust in
              agricultural commerce.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Feature Card */}
            <FeatureCard
              title="For Consumers"
              points={[
                "Browse authentic agricultural products",
                "AI-verified GI-tagged products",
                "Direct from farmers",
                "Fresh seasonal marketplace",
              ]}
            />

            <FeatureCard
              title="For Farmers"
              points={[
                "List products easily",
                "AI marketing content generation",
                "Reach nationwide consumers",
                "Sales analytics tracking",
              ]}
            />

            <FeatureCard
              title="AI Technology"
              points={[
                "Amazon Bedrock fraud detection",
                "Authenticity confidence scoring",
                "Market price prediction",
                "Automated content generation",
              ]}
            />
          </div>
        </div>
      </div>

      {/* FINAL CTA */}
      <div className="bg-gradient-to-r from-primary to-secondary py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>

          <p className="text-lg text-white/90 mb-8 max-w-2xl mx-auto">
            Join farmers and consumers building trust in agricultural commerce.
          </p>

          <Link
            to="/register"
            className="inline-flex items-center gap-2 bg-white text-primary px-8 py-4 rounded-xl text-lg font-semibold shadow-lg hover:shadow-xl transition"
          >
            Create Your Account
          </Link>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ title, points }: { title: string; points: string[] }) {
  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border hover:shadow-lg transition">
      <h3 className="text-xl font-bold text-gray-900 mb-4">{title}</h3>

      <ul className="space-y-3 text-gray-600">
        {points.map((point: string, i: number) => (
          <li key={i} className="flex items-start gap-2">
            <svg
              className="w-4 h-4 text-primary mt-1 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            {point}
          </li>
        ))}
      </ul>
    </div>
  );
}
