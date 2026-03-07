import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../../services/api";
import CheckoutFlow from "../../components/consumer/CheckoutFlow";
import ReferralShareButton from "../../components/consumer/ReferralShareButton";
import type { Product } from "../../types";

export default function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCheckout, setShowCheckout] = useState(false);

  useEffect(() => {
    if (productId) {
      loadProduct();
    }
  }, [productId]);

  const loadProduct = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/products/${productId}`);
      setProduct(response.data);
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to load product");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
          <p className="mt-4 text-gray-600">Loading product...</p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 text-lg mb-4">
            {error || "Product not found"}
          </p>
          <Link
            to="/consumer/dashboard"
            className="text-green-600 hover:text-green-700"
          >
            ← Back to marketplace
          </Link>
        </div>
      </div>
    );
  }

  if (showCheckout) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="container mx-auto px-4">
          <CheckoutFlow
            productId={product.productId}
            productName={product.name}
            price={product.price}
            unit={product.unit}
            onCancel={() => setShowCheckout(false)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <Link
          to="/consumer/dashboard"
          className="text-green-600 hover:text-green-700 mb-6 inline-block"
        >
          ← Back to marketplace
        </Link>

        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <div className="grid md:grid-cols-2 gap-8 p-8">
            <div>
              {product.images && product.images.length > 0 ? (
                <img
                  src={product.images[0].url}
                  alt={product.name}
                  className="w-full h-96 object-cover rounded-lg"
                />
              ) : (
                <div className="w-full h-96 bg-gray-200 rounded-lg flex items-center justify-center">
                  <span className="text-gray-400">No image available</span>
                </div>
              )}
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-4">
                {product.name}
              </h1>

              {product.giTag?.hasTag && (
                <div className="mb-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    ✓ GI Tagged: {product.giTag.tagName}
                  </span>
                </div>
              )}

              <div className="mb-6">
                <span className="text-3xl font-bold text-gray-900">
                  ₹{product.price}
                </span>
                <span className="text-gray-600 ml-2">per {product.unit}</span>
              </div>

              {product.authenticityConfidence && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm font-semibold text-blue-900 mb-1">
                    Authenticity Score
                  </p>
                  <p className="text-2xl font-bold text-blue-600">
                    {product.authenticityConfidence}%
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    AI-verified authentic product
                  </p>
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Description
                </h3>
                <p className="text-gray-600">{product.description}</p>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Details
                </h3>
                <dl className="grid grid-cols-2 gap-4">
                  <div>
                    <dt className="text-sm text-gray-500">Category</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {product.category}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">
                      Available Quantity
                    </dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {product.quantity} {product.unit}
                    </dd>
                  </div>
                  {product.seasonal?.isSeasonal && (
                    <>
                      <div>
                        <dt className="text-sm text-gray-500">Season Start</dt>
                        <dd className="text-sm font-medium text-gray-900">
                          {product.seasonal.seasonStart
                            ? new Date(
                                product.seasonal.seasonStart,
                              ).toLocaleDateString()
                            : "N/A"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-sm text-gray-500">Season End</dt>
                        <dd className="text-sm font-medium text-gray-900">
                          {product.seasonal.seasonEnd
                            ? new Date(
                                product.seasonal.seasonEnd,
                              ).toLocaleDateString()
                            : "N/A"}
                        </dd>
                      </div>
                    </>
                  )}
                </dl>
              </div>

              <button
                onClick={() => setShowCheckout(true)}
                className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition mb-3"
              >
                Purchase Now
              </button>

              <ReferralShareButton
                productId={product.productId}
                productName={product.name}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
