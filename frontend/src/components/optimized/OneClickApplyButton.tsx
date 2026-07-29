/**
 * OneClickApplyButton - Optimized apply button with loading states
 * Features:
 * - Single click application
 * - Loading state with spinner
 * - Success confirmation
 * - Error handling
 * - Sticky positioning for mobile
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface OneClickApplyButtonProps {
  jobId: string;
  cvId?: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
  className?: string;
}

export const OneClickApplyButton: React.FC<OneClickApplyButtonProps> = ({
  jobId,
  cvId,
  onSuccess,
  onError,
  className = ''
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleApply = async () => {
    if (!cvId) {
      onError?.("Veuillez d'abord télécharger votre CV");
      return;
    }

    setIsLoading(true);
    setIsSuccess(false);

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      // In real implementation:
      // const response = await applyToJob(jobId, cvId);

      setIsSuccess(true);
      onSuccess?.();

      // Reset after 3 seconds
      setTimeout(() => setIsSuccess(false), 3000);
    } catch (error) {
      onError?.(error instanceof Error ? error.message : 'Erreur de candidature');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.button
      onClick={handleApply}
      disabled={isLoading || isSuccess}
      className={`w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 ${className}`}
      whileTap={{ scale: 0.98 }}
    >
      {isLoading ? (
        <div className="flex items-center justify-center">
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Traitement...
        </div>
      ) : isSuccess ? (
        <div className="flex items-center justify-center">
          ✅ Candidature envoyée !
        </div>
      ) : (
        <div className="flex items-center justify-center">
          🚀 Postuler en 1 clic
        </div>
      )}
    </motion.button>
  );
};

export default OneClickApplyButton;