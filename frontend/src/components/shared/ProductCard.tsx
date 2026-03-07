import React from "react";
import { useNavigate } from "react-router-dom";
import type { Product } from "../../types";

interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/products/${product.productId}`);
  };

  const primaryImage =
    product.images.find((img) => img.isPrimary) || product.images[0];

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-2xl shadow-lg overflow-hidden cursor-pointer hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 card-hover"
    >
      {/* Product Image */}
      <div className="relative h-56 bg-gradient-to-br from-gray-100 to-gray-200">
        {primaryImage ? (
          <img
            src={primaryImage.url}
            alt={product.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-gray-400">
            <svg
              className="w-16 h-16 mb-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-sm">No Image</span>
          </div>
        )}

        {/* Badges Container */}
        <div className="absolute top-3 left-3 right-3 flex justify-between items-start">
          {/* Authenticity Score */}
          {product.authenticityConfidence &&
            product.authenticityConfidence >= 80 && (
              <div className="bg-primary text-white px-3 py-1.5 rounded-full text-xs font-semibold shadow-lg flex items-center">
                <svg
                  className="w-3.5 h-3.5 mr-1"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                {product.authenticityConfidence}% Verified
              </div>
            )}

          {/* GI Badge */}
          {product.giTag.hasTag && (
            <div className="bg-accent text-white px-3 py-1.5 rounded-full text-xs font-bold shadow-lg flex items-center">
              <svg
                className="w-3.5 h-3.5 mr-1"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              GI TAG
            </div>
          )}
        </div>
      </div>

      {/* Product Details */}
      <div className="p-5">
        <h3 className="text-xl font-bold text-gray-900 mb-2 truncate">
          {product.name}
        </h3>

        <p className="text-sm text-gray-600 mb-4 flex items-center">
          <svg
            className="w-4 h-4 mr-1.5 text-secondary"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
              clipRule="evenodd"
            />
          </svg>
          {product.farmerName || "Unknown Farmer"}
        </p>

        {/* Price and Rating */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-100">
          <div>
            <div className="text-2xl font-bold text-primary">
              ₹{product.price}
            </div>
            <div className="text-xs text-gray-500">per {product.unit}</div>
          </div>

          {product.averageRating > 0 && (
            <div className="flex items-center bg-yellow-50 px-3 py-1.5 rounded-lg">
              <svg
                className="w-4 h-4 text-yellow-500 fill-current"
                viewBox="0 0 20 20"
              >
                <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
              </svg>
              <span className="ml-1.5 text-sm font-semibold text-gray-900">
                {product.averageRating.toFixed(1)}
              </span>
              <span className="ml-1 text-xs text-gray-500">
                ({product.totalReviews})
              </span>
            </div>
          )}
        </div>

        {/* Scarcity Indicators */}
        <div className="space-y-2 mb-4">
          {/* Low Stock Warning */}
          {product.quantity > 0 && product.quantity < 10 && (
            <div className="flex items-center text-xs font-medium text-orange-600 bg-orange-50 px-3 py-2 rounded-lg">
              <svg
                className="w-4 h-4 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              Only {product.quantity} left in stock!
            </div>
          )}

          {/* Current Viewers */}
          {product.currentViewers > 0 && (
            <div className="flex items-center text-xs text-gray-600">
              <svg
                className="w-4 h-4 mr-2 text-gray-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                <path
                  fillRule="evenodd"
                  d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                  clipRule="evenodd"
                />
              </svg>
              {product.currentViewers} people viewing now
            </div>
          )}

          {/* Recent Purchases */}
          {product.recentPurchaseCount > 0 && (
            <div className="flex items-center text-xs text-secondary font-medium">
              <svg
                className="w-4 h-4 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M3 1a1 1 0 000 2h1.22l.305 1.222a.997.997 0 00.01.042l1.358 5.43-.893.892C3.74 11.846 4.632 14 6.414 14H15a1 1 0 000-2H6.414l1-1H14a1 1 0 00.894-.553l3-6A1 1 0 0017 3H6.28l-.31-1.243A1 1 0 005 1H3zM16 16.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM6.5 18a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" />
              </svg>
              {product.recentPurchaseCount} purchased recently
            </div>
          )}
        </div>

        {/* View Details Button */}
        <button className="w-full bg-primary hover:bg-primary/90 text-white font-semibold py-3 px-4 rounded-xl transition-colors duration-200 flex items-center justify-center">
          View Details
          <svg
            className="w-4 h-4 ml-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ProductCard;
