import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { X, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export default function ImageGalleryModal({ photos, initialIndex = 0, onClose }) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load image from Telegram
  const loadImage = useCallback(async (photoId) => {
    if (!photoId) return;
    
    setLoading(true);
    setError(null);
    setImageUrl(null);

    try {
      const response = await axios.get(`${API}/files/${photoId}/download-url`);
      setImageUrl(response.data.download_url);
    } catch (err) {
      console.error('Failed to load image:', err);
      setError('Failed to load image from Telegram');
      toast.error('Failed to load image');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load current image when index changes
  useEffect(() => {
    if (photos && photos[currentIndex]) {
      loadImage(photos[currentIndex].id);
    }
  }, [currentIndex, photos, loadImage]);

  // Navigation handlers
  const goToPrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : photos.length - 1));
  }, [photos.length]);

  const goToNext = useCallback(() => {
    setCurrentIndex((prev) => (prev < photos.length - 1 ? prev + 1 : 0));
  }, [photos.length]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft') {
        goToPrevious();
      } else if (e.key === 'ArrowRight') {
        goToNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, goToPrevious, goToNext]);

  if (!photos || photos.length === 0) {
    return null;
  }

  const currentPhoto = photos[currentIndex];

  return (
    <div
      className="fixed inset-0 z-50 bg-black bg-opacity-95 flex items-center justify-center"
      onClick={(e) => {
        // Close when clicking on backdrop
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      {/* Close Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onClose}
        className="absolute top-4 right-4 text-white hover:bg-white/20 z-10"
        title="Close (Esc)"
      >
        <X className="w-6 h-6" />
      </Button>

      {/* Image Counter */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 text-white text-sm font-medium bg-black/50 px-4 py-2 rounded-full">
        {currentIndex + 1} / {photos.length}
      </div>

      {/* Previous Button */}
      {photos.length > 1 && (
        <Button
          variant="ghost"
          size="icon"
          onClick={goToPrevious}
          className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white hover:bg-white/20 w-12 h-12"
          title="Previous (←)"
        >
          <ChevronLeft className="w-8 h-8" />
        </Button>
      )}

      {/* Next Button */}
      {photos.length > 1 && (
        <Button
          variant="ghost"
          size="icon"
          onClick={goToNext}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white hover:bg-white/20 w-12 h-12"
          title="Next (→)"
        >
          <ChevronRight className="w-8 h-8" />
        </Button>
      )}

      {/* Image Container */}
      <div className="max-w-7xl max-h-[90vh] w-full h-full flex items-center justify-center p-8">
        {loading && (
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-12 h-12 text-white animate-spin" />
            <p className="text-white text-sm">Loading image from Telegram...</p>
          </div>
        )}

        {error && (
          <div className="text-center">
            <p className="text-red-400 text-lg mb-4">{error}</p>
            <Button
              onClick={() => loadImage(currentPhoto.id)}
              className="bg-white text-black hover:bg-gray-200"
            >
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && imageUrl && (
          <div className="relative w-full h-full flex items-center justify-center">
            <img
              src={imageUrl}
              alt={currentPhoto.name}
              className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
              onError={() => {
                setError('Failed to load image');
              }}
            />
            
            {/* Image Info */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/70 text-white px-4 py-2 rounded-lg max-w-md">
              <p className="text-sm font-medium truncate" title={currentPhoto.name}>
                {currentPhoto.name}
              </p>
              {currentPhoto.size && (
                <p className="text-xs text-gray-300">
                  {formatFileSize(currentPhoto.size)}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}
