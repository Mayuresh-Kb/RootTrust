import { useState } from "react";
import { paymentApi, orderApi } from "../../services/api";

interface CheckoutFlowProps {
  productId: string;
  productName: string;
  price: number;
  unit: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export default function CheckoutFlow({
  productId,
  productName,
  price,
  unit,
  onCancel,
}: CheckoutFlowProps) {
  const [quantity, setQuantity] = useState(1);
  const [deliveryAddress, setDeliveryAddress] = useState({
    street: "",
    city: "",
    state: "",
    pincode: "",
  });
  const [referralCode, setReferralCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalAmount = price * quantity;

  const handleCheckout = async () => {
    try {
      setLoading(true);
      setError(null);

      // Validate address
      if (
        !deliveryAddress.street ||
        !deliveryAddress.city ||
        !deliveryAddress.state ||
        !deliveryAddress.pincode
      ) {
        setError("Please fill in all delivery address fields");
        return;
      }

      // Create order
      const orderResponse = await orderApi.create({
        productId,
        quantity,
        deliveryAddress,
        referralCode: referralCode || undefined,
      });

      // Initiate payment
      const paymentResponse = await paymentApi.initiate(orderResponse.orderId);

      // Redirect to payment gateway
      window.location.href = paymentResponse.paymentUrl;
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to process checkout");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Checkout</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Product Summary */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold text-gray-900 mb-2">Order Summary</h3>
        <div className="flex justify-between items-center mb-2">
          <span className="text-gray-600">{productName}</span>
          <span className="font-semibold">
            ₹{price}/{unit}
          </span>
        </div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-gray-600">Quantity:</label>
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            className="w-20 px-2 py-1 border border-gray-300 rounded"
          />
        </div>
        <div className="border-t pt-2 mt-2 flex justify-between items-center">
          <span className="font-bold text-gray-900">Total:</span>
          <span className="font-bold text-green-600 text-xl">
            ₹{totalAmount}
          </span>
        </div>
      </div>

      {/* Delivery Address */}
      <div className="mb-6">
        <h3 className="font-semibold text-gray-900 mb-3">Delivery Address</h3>
        <div className="space-y-3">
          <input
            type="text"
            placeholder="Street Address"
            value={deliveryAddress.street}
            onChange={(e) =>
              setDeliveryAddress({ ...deliveryAddress, street: e.target.value })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="City"
              value={deliveryAddress.city}
              onChange={(e) =>
                setDeliveryAddress({ ...deliveryAddress, city: e.target.value })
              }
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <input
              type="text"
              placeholder="State"
              value={deliveryAddress.state}
              onChange={(e) =>
                setDeliveryAddress({
                  ...deliveryAddress,
                  state: e.target.value,
                })
              }
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          <input
            type="text"
            placeholder="Pincode"
            value={deliveryAddress.pincode}
            onChange={(e) =>
              setDeliveryAddress({
                ...deliveryAddress,
                pincode: e.target.value,
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
      </div>

      {/* Referral Code */}
      <div className="mb-6">
        <h3 className="font-semibold text-gray-900 mb-3">
          Referral Code (Optional)
        </h3>
        <input
          type="text"
          placeholder="Enter referral code"
          value={referralCode}
          onChange={(e) => setReferralCode(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <button
          onClick={handleCheckout}
          disabled={loading}
          className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Processing..." : "Proceed to Payment"}
        </button>
        {onCancel && (
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition disabled:opacity-50"
          >
            Cancel
          </button>
        )}
      </div>

      <p className="mt-4 text-sm text-gray-500 text-center">
        You will be redirected to a secure payment gateway to complete your
        purchase
      </p>
    </div>
  );
}
