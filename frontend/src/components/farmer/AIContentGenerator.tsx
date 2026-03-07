import { useState } from "react";
import { aiApi } from "../../services/api";

interface AIContentGeneratorProps {
  productId: string;
  currentDescription?: string;
  onSelect?: (content: string) => void;
}

type ContentType = "description" | "names" | "social" | "launch" | "enhance";

export default function AIContentGenerator({
  productId,
  currentDescription,
  onSelect,
}: AIContentGeneratorProps) {
  const [contentType, setContentType] = useState<ContentType>("description");
  const [generatedContent, setGeneratedContent] = useState<string | string[]>(
    "",
  );
  const [selectedContent, setSelectedContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setError(null);
      setGeneratedContent("");

      let response;
      switch (contentType) {
        case "description":
          response = await aiApi.generateDescription(productId);
          setGeneratedContent(response.description);
          break;
        case "names":
          response = await aiApi.generateNames({ productId } as any);
          setGeneratedContent(response.names);
          break;
        case "social":
          response = await aiApi.generateSocial(productId);
          setGeneratedContent(response.socialText);
          break;
        case "launch":
          response = await aiApi.generateLaunch(productId);
          setGeneratedContent(response.launchText);
          break;
        case "enhance":
          if (!currentDescription) {
            setError("Please provide a description to enhance");
            return;
          }
          response = await aiApi.enhanceDescription(currentDescription);
          setGeneratedContent(response.enhancedDescription);
          break;
      }
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to generate content");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectContent = (content: string) => {
    setSelectedContent(content);
    if (onSelect) {
      onSelect(content);
    }
  };

  const contentTypeLabels = {
    description: "Product Description",
    names: "Product Name Suggestions",
    social: "Social Media Post",
    launch: "Launch Announcement",
    enhance: "Enhance Description",
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-xl font-bold text-gray-900 mb-4">
        AI Content Generator
      </h3>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Content Type
        </label>
        <select
          value={contentType}
          onChange={(e) => setContentType(e.target.value as ContentType)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          {Object.entries(contentTypeLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {contentType === "enhance" && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Current Description
          </label>
          <textarea
            value={currentDescription || ""}
            readOnly
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
          />
        </div>
      )}

      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed mb-4"
      >
        {loading ? "Generating..." : "Generate Content"}
      </button>

      {generatedContent && (
        <div className="mt-6">
          <h4 className="font-semibold text-gray-900 mb-3">
            Generated Content:
          </h4>

          {Array.isArray(generatedContent) ? (
            <div className="space-y-3">
              {generatedContent.map((item, index) => (
                <div
                  key={index}
                  className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                    selectedContent === item
                      ? "border-green-600 bg-green-50"
                      : "border-gray-200 hover:border-green-300"
                  }`}
                  onClick={() => handleSelectContent(item)}
                >
                  <div className="flex justify-between items-start">
                    <p className="text-gray-900">{item}</p>
                    {selectedContent === item && (
                      <svg
                        className="w-6 h-6 text-green-600 flex-shrink-0 ml-2"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                selectedContent === generatedContent
                  ? "border-green-600 bg-green-50"
                  : "border-gray-200 hover:border-green-300"
              }`}
              onClick={() => handleSelectContent(generatedContent)}
            >
              <div className="flex justify-between items-start">
                <p className="text-gray-900 whitespace-pre-wrap">
                  {generatedContent}
                </p>
                {selectedContent === generatedContent && (
                  <svg
                    className="w-6 h-6 text-green-600 flex-shrink-0 ml-2"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
            </div>
          )}

          {selectedContent && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800">
                ✓ Content selected! You can edit it before saving.
              </p>
            </div>
          )}

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Edit Selected Content (Optional)
            </label>
            <textarea
              value={selectedContent}
              onChange={(e) => setSelectedContent(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="Select content above or type your own..."
            />
          </div>
        </div>
      )}
    </div>
  );
}
