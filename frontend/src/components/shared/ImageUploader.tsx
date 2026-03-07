import React, { useState, useRef, useEffect } from "react";
import axios from "axios";

interface ImageUploaderProps {
  onUploadComplete: (urls: string[]) => void;
  maxFiles?: number;
  acceptedFormats?: string[];
  presignedUrls?: string[]; // Optional: if provided, will auto-upload
}

interface UploadProgress {
  file: File;
  progress: number;
  url?: string;
  error?: string;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onUploadComplete,
  maxFiles = 5,
  acceptedFormats = ["image/jpeg", "image/png", "image/jpg"],
  presignedUrls,
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-upload when presigned URLs are provided
  useEffect(() => {
    if (presignedUrls && presignedUrls.length > 0 && files.length > 0) {
      handleUpload(presignedUrls);
    }
  }, [presignedUrls]);

  const handleFileSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const validFiles: File[] = [];
    const newPreviews: string[] = [];

    Array.from(selectedFiles).forEach((file) => {
      if (acceptedFormats.includes(file.type)) {
        if (files.length + validFiles.length < maxFiles) {
          validFiles.push(file);
          const reader = new FileReader();
          reader.onloadend = () => {
            newPreviews.push(reader.result as string);
            if (newPreviews.length === validFiles.length) {
              setPreviews([...previews, ...newPreviews]);
            }
          };
          reader.readAsDataURL(file);
        }
      }
    });

    setFiles([...files, ...validFiles]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleRemoveFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index);
    const newPreviews = previews.filter((_, i) => i !== index);
    setFiles(newFiles);
    setPreviews(newPreviews);
  };

  const uploadToS3 = async (
    file: File,
    presignedUrl: string,
  ): Promise<string> => {
    await axios.put(presignedUrl, file, {
      headers: {
        "Content-Type": file.type,
      },
      onUploadProgress: (progressEvent) => {
        const progress = progressEvent.total
          ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
          : 0;
        setUploadProgress((prev) =>
          prev.map((p) => (p.file === file ? { ...p, progress } : p)),
        );
      },
    });

    // Extract the URL without query parameters
    return presignedUrl.split("?")[0];
  };

  const handleUpload = async (presignedUrls: string[]) => {
    if (files.length === 0) return;

    const initialProgress: UploadProgress[] = files.map((file) => ({
      file,
      progress: 0,
    }));
    setUploadProgress(initialProgress);

    try {
      const uploadPromises = files.map((file, index) =>
        uploadToS3(file, presignedUrls[index]),
      );

      const uploadedUrls = await Promise.all(uploadPromises);

      setUploadProgress((prev) =>
        prev.map((p, i) => ({ ...p, url: uploadedUrls[i], progress: 100 })),
      );

      onUploadComplete(uploadedUrls);
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadProgress((prev) =>
        prev.map((p) => ({
          ...p,
          error: "Upload failed",
        })),
      );
    }
  };

  return (
    <div className="w-full">
      {/* Drag and Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragging
            ? "border-green-500 bg-green-50"
            : "border-gray-300 hover:border-green-400"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedFormats.join(",")}
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />

        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        <p className="mt-2 text-sm text-gray-600">
          <span className="font-semibold">Click to upload</span> or drag and
          drop
        </p>
        <p className="text-xs text-gray-500">
          PNG, JPG up to 5MB (max {maxFiles} files)
        </p>
      </div>

      {/* Preview Grid */}
      {previews.length > 0 && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
          {previews.map((preview, index) => (
            <div key={index} className="relative group">
              <img
                src={preview}
                alt={`Preview ${index + 1}`}
                className="w-full h-32 object-cover rounded-lg"
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveFile(index);
                }}
                className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>

              {/* Upload Progress */}
              {uploadProgress[index] && uploadProgress[index].progress > 0 && (
                <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 rounded-b-lg p-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full transition-all"
                      style={{ width: `${uploadProgress[index].progress}%` }}
                    />
                  </div>
                  {uploadProgress[index].error && (
                    <p className="text-xs text-red-400 mt-1">
                      {uploadProgress[index].error}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* File Count */}
      {files.length > 0 && (
        <p className="mt-2 text-sm text-gray-600">
          {files.length} file{files.length !== 1 ? "s" : ""} selected
        </p>
      )}
    </div>
  );
};

// Export a helper function to be used by parent components
export const useImageUploader = () => {
  return {
    uploadToS3: async (file: File, presignedUrl: string) => {
      await axios.put(presignedUrl, file, {
        headers: {
          "Content-Type": file.type,
        },
      });
      return presignedUrl.split("?")[0];
    },
  };
};
