from typing import Dict, List

from megadetector.detection import run_detector_batch


class AnimalDetector:
    def __init__(self, model_path: str, min_conf: float = 0.2) -> None:
        self.model_path = model_path
        self.min_conf = min_conf

    def detect(self, image_path: str) -> List[Dict]:
        data = run_detector_batch.load_and_run_detector_batch(
            image_file_names=[image_path], model_file=self.model_path
        )
        if not data:
            return []

        detections = data[0].get("detections", [])
        animal_detections = []
        for d in detections:
            # MegaDetector category "1" means animal
            if str(d.get("category")) != "1":
                continue
            conf = float(d.get("conf", 0))
            if conf < self.min_conf:
                continue
            animal_detections.append(d)
        return animal_detections
