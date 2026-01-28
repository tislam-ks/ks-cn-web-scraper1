"""
Video Stitch Interpolator Node for ComfyUI (V3 API)
Seamlessly stitches multiple video clips using interpolation and crossfade.
"""

from __future__ import annotations

import torch
import numpy as np
from PIL import Image
import logging

from comfy_api.latest import io

logger = logging.getLogger(__name__)


def interpolate_frames(frame_a: torch.Tensor, frame_b: torch.Tensor, 
                      num_frames: int, method: str = "linear") -> list:
    """
    Generate interpolated frames between two frames.
    
    Args:
        frame_a: Starting frame tensor [H, W, C]
        frame_b: Ending frame tensor [H, W, C]
        num_frames: Number of intermediate frames to generate
        method: Interpolation method (linear, ease_in_out, cosine, sigmoid)
    
    Returns:
        List of interpolated frame tensors
    """
    if num_frames <= 0:
        return []
    
    interpolated = []
    
    for i in range(1, num_frames + 1):
        # Calculate blend factor based on method
        t = i / (num_frames + 1)  # Progress from 0 to 1
        
        if method == "linear":
            alpha = t
        elif method == "ease_in_out":
            # Smooth ease in/out curve
            alpha = t * t * (3 - 2 * t)
        elif method == "cosine":
            # Cosine interpolation (smoother)
            alpha = (1 - np.cos(t * np.pi)) / 2
        elif method == "sigmoid":
            # Sigmoid curve (sharper transition in middle)
            alpha = 1 / (1 + np.exp(-12 * (t - 0.5)))
        else:
            alpha = t
        
        # Blend frames
        blended = frame_a * (1 - alpha) + frame_b * alpha
        interpolated.append(blended)
    
    return interpolated


def crossfade_sequences(seq_a: torch.Tensor, seq_b: torch.Tensor,
                       crossfade_frames: int, method: str = "linear") -> torch.Tensor:
    """
    Apply crossfade between end of seq_a and start of seq_b.
    """
    len_a = seq_a.shape[0]
    len_b = seq_b.shape[0]
    
    # Limit crossfade to available frames
    crossfade_frames = min(crossfade_frames, len_a, len_b)
    
    if crossfade_frames <= 0:
        # No crossfade, just concatenate
        return torch.cat([seq_a, seq_b], dim=0)
    
    # Split sequences
    pre_fade_a = seq_a[:-crossfade_frames] if crossfade_frames < len_a else torch.empty(0, *seq_a.shape[1:])
    fade_a = seq_a[-crossfade_frames:]
    fade_b = seq_b[:crossfade_frames]
    post_fade_b = seq_b[crossfade_frames:] if crossfade_frames < len_b else torch.empty(0, *seq_b.shape[1:])
    
    # Generate crossfade frames
    crossfade_result = []
    for i in range(crossfade_frames):
        t = (i + 1) / (crossfade_frames + 1)
        
        if method == "linear":
            alpha = t
        elif method == "ease_in_out":
            alpha = t * t * (3 - 2 * t)
        elif method == "cosine":
            alpha = (1 - np.cos(t * np.pi)) / 2
        elif method == "sigmoid":
            alpha = 1 / (1 + np.exp(-12 * (t - 0.5)))
        else:
            alpha = t
        
        blended = fade_a[i] * (1 - alpha) + fade_b[i] * alpha
        crossfade_result.append(blended)
    
    crossfade_tensor = torch.stack(crossfade_result, dim=0) if crossfade_result else torch.empty(0, *seq_a.shape[1:])
    
    # Combine all parts
    parts = []
    if pre_fade_a.shape[0] > 0:
        parts.append(pre_fade_a)
    if crossfade_tensor.shape[0] > 0:
        parts.append(crossfade_tensor)
    if post_fade_b.shape[0] > 0:
        parts.append(post_fade_b)
    
    if parts:
        return torch.cat(parts, dim=0)
    else:
        return torch.cat([seq_a, seq_b], dim=0)


def resize_video_to_match(video_a: torch.Tensor, video_b: torch.Tensor) -> torch.Tensor:
    """Resize video_b frames to match video_a dimensions"""
    if video_a.shape[1:] == video_b.shape[1:]:
        return video_b
    
    logger.warning(f"Video dimensions differ: A={video_a.shape[1:]}, B={video_b.shape[1:]}")
    logger.warning("Resizing video_b to match video_a dimensions")
    
    h, w = video_a.shape[1], video_a.shape[2]
    resized_frames = []
    for frame in video_b:
        frame_np = (frame.cpu().numpy() * 255).astype(np.uint8)
        img = Image.fromarray(frame_np)
        img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
        frame_resized = torch.from_numpy(np.array(img_resized).astype(np.float32) / 255.0)
        resized_frames.append(frame_resized)
    return torch.stack(resized_frames, dim=0).to(video_a.device)


def stitch_two_videos(video_a: torch.Tensor, video_b: torch.Tensor,
                     overlap_frames: int, crossfade_frames: int,
                     interpolation_frames: int, interpolation_method: str) -> torch.Tensor:
    """Stitch two video clips together."""
    len_a = video_a.shape[0]
    len_b = video_b.shape[0]
    
    logger.info(f"Stitching video_a ({len_a} frames) with video_b ({len_b} frames)")
    logger.info(f"Settings: overlap={overlap_frames}, crossfade={crossfade_frames}, interp={interpolation_frames}")
    
    # Handle size mismatch
    video_b = resize_video_to_match(video_a, video_b)
    
    # Last frame of A and first frame of B for interpolation
    last_frame_a = video_a[-1]
    first_frame_b = video_b[0]
    
    # Generate interpolated frames
    interpolated = interpolate_frames(
        last_frame_a, first_frame_b, 
        interpolation_frames, 
        interpolation_method
    )
    
    if interpolation_frames > 0 and interpolated:
        # With interpolation: A (without last frame) + interpolated + B (without first frame)
        parts = [video_a[:-1]]
        parts.append(torch.stack(interpolated, dim=0))
        parts.append(video_b[1:])
    elif crossfade_frames > 0:
        # Without interpolation but with crossfade
        transition_start_a = max(0, len_a - overlap_frames)
        transition_end_b = min(overlap_frames, len_b)
        
        pre_transition = video_a[:transition_start_a]
        overlap_a = video_a[transition_start_a:]
        overlap_b = video_b[:transition_end_b]
        post_transition = video_b[transition_end_b:]
        
        transition = crossfade_sequences(
            overlap_a, overlap_b, 
            min(crossfade_frames, overlap_frames),
            interpolation_method
        )
        
        parts = []
        if pre_transition.shape[0] > 0:
            parts.append(pre_transition)
        parts.append(transition)
        if post_transition.shape[0] > 0:
            parts.append(post_transition)
    else:
        # No interpolation or crossfade - simple concatenation
        parts = [video_a, video_b]
    
    result = torch.cat([p for p in parts if p.shape[0] > 0], dim=0)
    logger.info(f"Stitched result: {result.shape[0]} frames")
    
    return result


class VideoStitchInterpolator(io.ComfyNode):
    """
    Stitches two or more video clips (IMAGE batches) together with smooth interpolation/crossfade.
    
    Takes the end frames of video_a and start frames of video_b, then:
    1. Optionally generates interpolated frames between them
    2. Applies crossfade blending for smooth transition
    3. Outputs a single seamless video
    """
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoStitchInterpolator",
            display_name="Video Stitch Interpolator",
            category="webscraper/video",
            inputs=[
                io.Image.Input(
                    "video_a",
                    tooltip="First video clip (batch of frames)"
                ),
                io.Image.Input(
                    "video_b",
                    tooltip="Second video clip (batch of frames)"
                ),
                io.Int.Input(
                    "overlap_frames",
                    default=4,
                    min=1,
                    max=30,
                    step=1,
                    tooltip="Number of frames from each clip to use for blending transition"
                ),
                io.Int.Input(
                    "crossfade_frames",
                    default=8,
                    min=0,
                    max=60,
                    step=1,
                    tooltip="Total frames for crossfade transition (0 = hard cut)"
                ),
                io.Int.Input(
                    "interpolation_frames",
                    default=2,
                    min=0,
                    max=30,
                    step=1,
                    tooltip="Number of interpolated frames to generate between clips (0 = no interpolation)"
                ),
                io.Combo.Input(
                    "interpolation_method",
                    options=["linear", "ease_in_out", "cosine", "sigmoid"],
                    default="ease_in_out",
                    tooltip="Curve type for interpolation blending"
                ),
            ],
            outputs=[
                io.Image.Output(
                    display_name="stitched_video",
                    tooltip="Seamlessly stitched video frames"
                )
            ],
        )
    
    @classmethod
    def execute(cls, video_a, video_b, overlap_frames, crossfade_frames,
               interpolation_frames, interpolation_method) -> io.NodeOutput:
        """Main entry point - stitch two videos together."""
        logger.info("=" * 50)
        logger.info("Video Stitch Interpolator - Starting")
        logger.info("=" * 50)
        
        result = stitch_two_videos(
            video_a, video_b,
            overlap_frames, crossfade_frames,
            interpolation_frames, interpolation_method
        )
        
        logger.info(f"Final stitched video: {result.shape[0]} frames, {result.shape[1]}x{result.shape[2]}")
        logger.info("=" * 50)
        
        return io.NodeOutput(result)


class VideoStitchMultiple(io.ComfyNode):
    """
    🎬 ONE NODE TO STITCH THEM ALL! 
    Stitches up to 8 video clips together into one seamless long video.
    Just connect your video clips and it handles all the interpolation/crossfade automatically.
    """
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoStitchMultiple",
            display_name="🎬 Video Stitch All",
            category="webscraper/video",
            description="Stitch up to 8 videos into one seamless long video with automatic interpolation",
            inputs=[
                io.Image.Input(
                    "video_1",
                    tooltip="First video clip (required)"
                ),
                io.Image.Input(
                    "video_2",
                    tooltip="Second video clip (required)"
                ),
                io.Image.Input(
                    "video_3",
                    optional=True,
                    tooltip="Third video clip (optional)"
                ),
                io.Image.Input(
                    "video_4",
                    optional=True,
                    tooltip="Fourth video clip (optional)"
                ),
                io.Image.Input(
                    "video_5",
                    optional=True,
                    tooltip="Fifth video clip (optional)"
                ),
                io.Image.Input(
                    "video_6",
                    optional=True,
                    tooltip="Sixth video clip (optional)"
                ),
                io.Image.Input(
                    "video_7",
                    optional=True,
                    tooltip="Seventh video clip (optional)"
                ),
                io.Image.Input(
                    "video_8",
                    optional=True,
                    tooltip="Eighth video clip (optional)"
                ),
                io.Int.Input(
                    "interpolation_frames",
                    default=4,
                    min=0,
                    max=30,
                    step=1,
                    tooltip="Number of AI-generated in-between frames at each transition (smoother = more frames)"
                ),
                io.Int.Input(
                    "crossfade_frames",
                    default=8,
                    min=0,
                    max=30,
                    step=1,
                    tooltip="Number of frames to crossfade/blend at each transition"
                ),
                io.Int.Input(
                    "overlap_frames",
                    default=4,
                    min=1,
                    max=20,
                    step=1,
                    tooltip="Frames from each clip to use for the transition zone"
                ),
                io.Combo.Input(
                    "interpolation_method",
                    options=["ease_in_out", "linear", "cosine", "sigmoid"],
                    default="ease_in_out",
                    tooltip="Blending curve: ease_in_out (smooth), linear (constant), cosine (natural), sigmoid (sharp middle)"
                ),
            ],
            outputs=[
                io.Image.Output(
                    display_name="long_video",
                    tooltip="All clips stitched together into one seamless video"
                ),
                io.Int.Output(
                    display_name="total_frames",
                    tooltip="Total number of frames in the output video"
                ),
            ],
        )
    
    @classmethod
    def execute(cls, video_1, video_2, interpolation_frames, crossfade_frames, 
                overlap_frames, interpolation_method,
                video_3=None, video_4=None, video_5=None, 
                video_6=None, video_7=None, video_8=None) -> io.NodeOutput:
        """Stitch all provided videos together into one long seamless video."""
        
        logger.info("=" * 60)
        logger.info("🎬 VIDEO STITCH ALL - Creating long seamless video")
        logger.info("=" * 60)
        
        # Collect all non-None videos
        all_videos = [video_1, video_2]
        optional_videos = [video_3, video_4, video_5, video_6, video_7, video_8]
        
        for i, vid in enumerate(optional_videos, start=3):
            if vid is not None and vid.shape[0] > 0:
                all_videos.append(vid)
                logger.info(f"Video {i}: {vid.shape[0]} frames")
        
        logger.info(f"Total videos to stitch: {len(all_videos)}")
        logger.info(f"Settings: interp={interpolation_frames}, crossfade={crossfade_frames}, overlap={overlap_frames}, method={interpolation_method}")
        
        # Start with first video
        result = all_videos[0]
        logger.info(f"Starting with video_1: {result.shape[0]} frames, {result.shape[1]}x{result.shape[2]}")
        
        # Stitch each subsequent video
        for i, next_video in enumerate(all_videos[1:], start=2):
            logger.info(f"Stitching video_{i} ({next_video.shape[0]} frames)...")
            
            result = stitch_two_videos(
                result, next_video,
                overlap_frames, crossfade_frames,
                interpolation_frames, interpolation_method
            )
            
            logger.info(f"After stitching video_{i}: {result.shape[0]} total frames")
        
        total_frames = result.shape[0]
        
        logger.info("=" * 60)
        logger.info(f"✅ COMPLETE: {total_frames} frames, {result.shape[1]}x{result.shape[2]}")
        logger.info(f"   Videos stitched: {len(all_videos)}")
        logger.info("=" * 60)
        
        return io.NodeOutput(result, total_frames)


class VideoFrameBlender(io.ComfyNode):
    """
    Simple node to blend/mix two video frame sequences.
    Useful for creating transitions or overlays.
    """
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoFrameBlender",
            display_name="Video Frame Blender",
            category="webscraper/video",
            inputs=[
                io.Image.Input(
                    "frames_a",
                    tooltip="First frame sequence"
                ),
                io.Image.Input(
                    "frames_b",
                    tooltip="Second frame sequence"
                ),
                io.Float.Input(
                    "blend_factor",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    tooltip="0.0 = all frames_a, 1.0 = all frames_b"
                ),
                io.Combo.Input(
                    "blend_mode",
                    options=["mix", "add", "multiply", "screen", "overlay"],
                    default="mix",
                ),
            ],
            outputs=[
                io.Image.Output(
                    display_name="blended_frames",
                    tooltip="Blended frame sequence"
                )
            ],
        )
    
    @classmethod
    def execute(cls, frames_a, frames_b, blend_factor, blend_mode) -> io.NodeOutput:
        """Blend two frame sequences together."""
        # Ensure same number of frames (use minimum)
        min_frames = min(frames_a.shape[0], frames_b.shape[0])
        a = frames_a[:min_frames]
        b = frames_b[:min_frames]
        
        # Handle size mismatch
        b = resize_video_to_match(a, b)
        
        if blend_mode == "mix":
            result = a * (1 - blend_factor) + b * blend_factor
        elif blend_mode == "add":
            result = torch.clamp(a + b * blend_factor, 0, 1)
        elif blend_mode == "multiply":
            result = a * (b * blend_factor + (1 - blend_factor))
        elif blend_mode == "screen":
            result = 1 - (1 - a) * (1 - b * blend_factor)
        elif blend_mode == "overlay":
            mask = a < 0.5
            result = torch.where(
                mask,
                2 * a * b * blend_factor,
                1 - 2 * (1 - a) * (1 - b * blend_factor)
            )
        else:
            result = a * (1 - blend_factor) + b * blend_factor
        
        return io.NodeOutput(torch.clamp(result, 0, 1))


class VideoLoopSeamless(io.ComfyNode):
    """
    Creates a seamless loop from a video by blending start and end frames.
    """
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoLoopSeamless",
            display_name="Video Loop Seamless",
            category="webscraper/video",
            inputs=[
                io.Image.Input(
                    "video",
                    tooltip="Input video frames"
                ),
                io.Int.Input(
                    "blend_frames",
                    default=8,
                    min=2,
                    max=60,
                    step=1,
                    tooltip="Number of frames to blend for seamless loop"
                ),
                io.Combo.Input(
                    "blend_curve",
                    options=["linear", "ease_in_out", "cosine"],
                    default="ease_in_out",
                ),
            ],
            outputs=[
                io.Image.Output(
                    display_name="looped_video",
                    tooltip="Seamlessly looping video"
                )
            ],
        )
    
    @classmethod
    def execute(cls, video, blend_frames, blend_curve) -> io.NodeOutput:
        """Create a seamless loop by blending end back to start."""
        num_frames = video.shape[0]
        blend_frames = min(blend_frames, num_frames // 2)
        
        if blend_frames < 2:
            return io.NodeOutput(video)
        
        # Get start and end regions
        start_region = video[:blend_frames]
        end_region = video[-blend_frames:]
        middle = video[blend_frames:-blend_frames]
        
        # Create blended transition
        blended = []
        for i in range(blend_frames):
            t = i / (blend_frames - 1)
            
            if blend_curve == "linear":
                alpha = t
            elif blend_curve == "ease_in_out":
                alpha = t * t * (3 - 2 * t)
            elif blend_curve == "cosine":
                alpha = (1 - np.cos(t * np.pi)) / 2
            else:
                alpha = t
            
            # Blend end frame towards start frame
            frame = end_region[i] * (1 - alpha) + start_region[i] * alpha
            blended.append(frame)
        
        blended_tensor = torch.stack(blended, dim=0)
        
        # Combine: start + middle + blended transition
        if middle.shape[0] > 0:
            result = torch.cat([start_region, middle, blended_tensor], dim=0)
        else:
            result = torch.cat([start_region, blended_tensor], dim=0)
        
        logger.info(f"Created seamless loop: {result.shape[0]} frames with {blend_frames} frame blend")
        
        return io.NodeOutput(result)
