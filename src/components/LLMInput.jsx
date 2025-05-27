import React, { useState } from "react";
import { ChevronUp, X } from "lucide-react";
import ReviewRAG from "./ReviewRAG";
import Cards from "./Cards";

export default function LLMInput() {
  const [message, setMessage] = useState("");
  const [features, setFeatures] = useState([]);
  const [isVisible, setIsVisible] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = () => {
    if (!message.trim()) return;
    setLoading(true);

    const apiResponse = [
      {
        title: "Elite camera system",
        subtitle: "50MP OIS, 8MP ultra-wide",
      },
      {
        title: "32 MP front camera",
        subtitle: "You in your best light",
      },
      {
        title: "TrueLens Engine 3",
        subtitle: "Advanced camera software, powered by AI",
      },
      {
        title: "TrueLens Engine 3",
        subtitle: "Advanced camera software, powered by AI",
      },
    ];

    // simulate API call
    setTimeout(() => {
      setFeatures(apiResponse); // update without hiding
      setIsVisible(true); // keep showing
      setLoading(false);
    }, 500);
  };

  const clearOutput = () => {
    setIsVisible(false);
    setTimeout(() => {
      setFeatures([]);
    }, 300); // match animation duration
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 flex-col gap-6">
      <ReviewRAG />

      <div className="w-full">
        {/* Input Box */}
        <div className="bg-gray-700 rounded-2xl border border-gray-700 p-4 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="How can I help you today?"
                className="w-full bg-transparent text-gray-300 placeholder-gray-500 text-lg resize-none border-none outline-none"
                rows="1"
                style={{ minHeight: "28px", maxHeight: "200px" }}
                onInput={(e) => {
                  e.target.style.height = "auto";
                  e.target.style.height = e.target.scrollHeight + "px";
                }}
              />
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button
                className={`w-8 h-8 rounded-lg transition-colors flex items-center justify-center ${
                  message.trim()
                    ? "bg-blue-500 hover:bg-orange-600 text-white"
                    : "bg-gray-700 text-gray-500 cursor-not-allowed"
                }`}
                onClick={handleSubmit}
                disabled={!message.trim()}
              >
                <ChevronUp className="w-4 h-4" />
              </button>

              {features.length > 0 && (
                <button
                  className="w-8 h-8 rounded-lg bg-red-500 text-white hover:bg-red-600 flex items-center justify-center"
                  onClick={clearOutput}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="text-center text-gray-500 text-xs mt-3">
          Application only provides guidance, do your own due diligence before
          making a purchase.
        </div>

        {/* Cards Animated Block */}
        <div
          className={`transform transition-all duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
            isVisible
              ? "opacity-100 translate-y-0"
              : "opacity-0 translate-y-10 pointer-events-none"
          }`}
        >
          {features.length > 0 && <Cards features={features} />}
        </div>
      </div>
    </div>
  );
}
