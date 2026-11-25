from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class InspectionCompareRequest(BaseModel):
    prev_inspection_id: int
    curr_inspection_id: int


class ImageComparisonResponse(BaseModel):
    id: int
    prev_image_id: int
    curr_image_id: int
    status: str
    inliers: Optional[int] = None
    inlier_ratio: Optional[float] = None
    reprojection_rmse: Optional[float] = None
    overlap_share: Optional[float] = None
    overlay_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectionComparisonResponse(BaseModel):
    comparison_id: int
    asset_id: int
    prev_inspection_id: int
    curr_inspection_id: int
    created_by: Optional[int] = None
    summary_json: Optional[str] = None
    created_at: datetime
    image_comparisons: List[ImageComparisonResponse] = []

    model_config = ConfigDict(from_attributes=True)
