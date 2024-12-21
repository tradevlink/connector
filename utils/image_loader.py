import os
from PIL import Image
import customtkinter as ctk

class ImageLoader:
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ImageLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    
    def get_image(self, image_name: str, size: tuple = None, preserve_ratio: bool = False) -> ctk.CTkImage:
        """
        Load an image from the assets directory and return it as CTkImage.
        
        Args:
            image_name (str): Name of the image file (e.g., 'settings.png')
            size (tuple, optional): Desired size as (width, height). If None, uses original size.
            preserve_ratio (bool): If True, maintains aspect ratio when resizing
        
        Returns:
            CTkImage: The loaded and possibly resized image
        """
        cache_key = f"{image_name}_{size}_{preserve_ratio}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        image_path = os.path.join(self.assets_dir, image_name)
        if not os.path.exists(image_path):
            print(f"Warning: Image {image_name} not found in assets directory")
            return None
            
        try:
            pil_image = Image.open(image_path)
            
            if size and preserve_ratio:
                # Calculate new size maintaining aspect ratio
                original_width, original_height = pil_image.size
                target_width, target_height = size
                
                # Calculate ratios
                width_ratio = target_width / original_width
                height_ratio = target_height / original_height
                
                # Use the smaller ratio to fit within the target size
                ratio = min(width_ratio, height_ratio)
                
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                size = (new_width, new_height)  # Update size for CTkImage
            elif size:
                pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
            
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
            self._cache[cache_key] = ctk_image
            return ctk_image
            
        except Exception as e:
            print(f"Error loading image {image_name}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the image cache to free up memory."""
        self._cache.clear()
