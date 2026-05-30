from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image


class SpeciesClassifier:
    def __init__(self, model_path: str, labels_path: str) -> None:
        self.device = self._select_device()
        self.classes = self._load_labels(labels_path)
        self.model = torch.load(model_path, map_location=self.device, weights_only=False)
        self.model.eval()
        self.model.to(self.device)
        self.transform = transforms.Compose(
            [
                transforms.Resize((480, 480)),
                transforms.ToTensor(),
            ]
        )

    @staticmethod
    def _select_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    @staticmethod
    def _load_labels(labels_path: str) -> List[str]:
        labels = []
        with open(labels_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) >= 6 and parts[5]:
                    labels.append(parts[5].strip().lower().replace(" ", "_"))
        if not labels:
            raise ValueError("labels.txt is empty or invalid")
        return labels

    @torch.no_grad()
    def classify(self, image_path: str) -> Tuple[str, float]:
        img = Image.open(image_path).convert("RGB")
        img = self.transform(img)
        img = img.unsqueeze(0)
        img = img.permute(0, 2, 3, 1)
        img = img.to(self.device)

        logits = self.model(img)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        best_idx = int(np.argmax(probs))
        species = self.classes[best_idx] if best_idx < len(self.classes) else "unknown"
        return species, float(probs[best_idx])
