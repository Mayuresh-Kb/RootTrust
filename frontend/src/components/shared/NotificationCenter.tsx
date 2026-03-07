import React, { useState, useEffect } from "react";
import { notificationApi } from "../../services/api";
import type { NotificationPreferences } from "../../types";

export const NotificationCenter: React.FC = () => {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    newProducts: true,
    promotions: true,
    orderUpdates: true,
    reviewRequests: true,
    limitedReleases: true,
    farmerBonuses: true,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    // In a real implementation, we would fetch current preferences from the API
    // For now, we'll use the default values
  }, []);

  const handleToggle = (key: keyof NotificationPreferences) => {
    setPreferences({
      ...preferences,
      [key]: !preferences[key],
    });
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      await notificationApi.updatePreferences(preferences);
      setMessage({
        type: "success",
        text: "Notification preferences updated successfully!",
      });
    } catch (error) {
      console.error("Failed to update preferences:", error);
      setMessage({
        type: "error",
        text: "Failed to update preferences. Please try again.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const notificationOptions = [
    {
      key: "newProducts" as keyof NotificationPreferences,
      label: "New Products",
      description: "Get notified when new seasonal products are launched",
    },
    {
      key: "promotions" as keyof NotificationPreferences,
      label: "Promotions",
      description: "Receive updates about special offers and promotions",
    },
    {
      key: "orderUpdates" as keyof NotificationPreferences,
      label: "Order Updates",
      description: "Get notified about your order status changes",
    },
    {
      key: "reviewRequests" as keyof NotificationPreferences,
      label: "Review Requests",
      description: "Receive reminders to review your purchases",
    },
    {
      key: "limitedReleases" as keyof NotificationPreferences,
      label: "Limited Releases",
      description: "Be the first to know about exclusive limited releases",
    },
    {
      key: "farmerBonuses" as keyof NotificationPreferences,
      label: "Farmer Bonuses",
      description: "Get notified about bonus achievements (for farmers)",
    },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-2 text-gray-800">
        Notification Preferences
      </h2>
      <p className="text-sm text-gray-600 mb-6">
        Choose which notifications you'd like to receive via email
      </p>

      {message && (
        <div
          className={`mb-4 p-3 rounded ${
            message.type === "success"
              ? "bg-green-100 border border-green-400 text-green-700"
              : "bg-red-100 border border-red-400 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="space-y-4">
        {notificationOptions.map((option) => (
          <div
            key={option.key}
            className="flex items-start justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex-1">
              <h3 className="text-base font-semibold text-gray-800">
                {option.label}
              </h3>
              <p className="text-sm text-gray-600 mt-1">{option.description}</p>
            </div>

            <button
              onClick={() => handleToggle(option.key)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 ${
                preferences[option.key] ? "bg-green-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  preferences[option.key] ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? "Saving..." : "Save Preferences"}
        </button>
      </div>

      <div className="mt-6 pt-6 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Note: Transactional emails (order confirmations, shipping updates)
          will always be sent regardless of these preferences.
        </p>
      </div>
    </div>
  );
};
