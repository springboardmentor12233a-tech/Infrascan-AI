from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InspectionComparison(Base):
    __tablename__ = "inspection_comparisons"

    comparison_id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    prev_inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=False, index=True)
    curr_inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    summary_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("InfrastructureAsset")
    prev_inspection = relationship("Inspection", foreign_keys=[prev_inspection_id])
    curr_inspection = relationship("Inspection", foreign_keys=[curr_inspection_id])
    creator = relationship("User", foreign_keys=[created_by])
    image_comparisons = relationship("ImageComparison", back_populates="comparison", cascade="all, delete-orphan")


class ImageComparison(Base):
    __tablename__ = "image_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(Integer, ForeignKey("inspection_comparisons.comparison_id", ondelete="CASCADE"), nullable=False, index=True)
    prev_image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    curr_image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False)  # "ok", "not_comparable", "failed"
    inliers = Column(Integer, nullable=True)
    inlier_ratio = Column(Float, nullable=True)
    reprojection_rmse = Column(Float, nullable=True)
    overlap_share = Column(Float, nullable=True)
    homography_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    warnings_json = Column(Text, nullable=True)
    overlay_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    comparison = relationship("InspectionComparison", back_populates="image_comparisons")
    prev_image = relationship("Image", foreign_keys=[prev_image_id])
    curr_image = relationship("Image", foreign_keys=[curr_image_id])
