# Docker Image Optimization Analysis

## Current State (PR #216)

**Approach**: Use jrottenberg/ffmpeg as base, install Python on top
**VAAPI Image Size**: 837MB
**NVIDIA Image Size**: 1.81GB

### Pros
- Works reliably (fixes the broken build)
- Latest FFmpeg version with all features
- Proven approach for GPU acceleration

### Cons
- Large image size (600+MB overhead)
- Installing full Python stack on top of FFmpeg base
- Maintenance depends on jrottenberg updates

## Proposed Optimization

**Approach**: Use python:3-slim as base, install Debian's FFmpeg package
**VAAPI Image Size**: 637MB with .dockerignore (200MB savings, 24% smaller)
**NVIDIA Image Size**: Expected ~480MB (73% smaller!)

### Pros
- **Significantly smaller images**
- Simpler Dockerfiles (no multi-stage complexity)
- Both VAAPI and NVENC support in single FFmpeg package
- Better integration with Python base (no library conflicts)
- Automatic security updates via Debian
- Could potentially use single Dockerfile for both GPU types

### Cons
- FFmpeg version tied to Debian stable (currently 7.1.2)
- Less control over FFmpeg build configuration
- Dependency on Debian package maintenance

## Technical Comparison

| Aspect | jrottenberg/ffmpeg | Debian FFmpeg |
|--------|-------------------|---------------|
| FFmpeg Version | 7.0+ (latest) | 7.1.2 (Debian stable) |
| VAAPI Support | ✓ | ✓ |
| NVENC Support | ✓ | ✓ |
| Image Size (VAAPI) | 837MB | 637MB |
| Image Size (NVIDIA) | 1.81GB | ~480MB |
| Library Conflicts | None | None |
| Maintenance | Community | Debian Team |
| Security Updates | Manual | Automatic |

## FFmpeg Capabilities Comparison

Both approaches provide the required encoders:

**Debian FFmpeg 7.1.2** includes:
- h264_vaapi, hevc_vaapi, vp8_vaapi, vp9_vaapi, av1_vaapi
- h264_nvenc, hevc_nvenc, av1_nvenc
- All standard codecs (libx264, libx265, etc.)

**jrottenberg/ffmpeg 7.0** includes:
- All of the above plus additional experimental features

For tesla_dashcam use case, both provide everything needed.

## Why Is The Image Still ~640MB?

The size breakdown:
- **Base python:3-slim**: ~115MB
- **FFmpeg + dependencies**: ~480MB
  - libllvm19: 127MB (OpenCL/GPU compute support)
  - mesa-libgallium: 42MB (Mesa graphics drivers)
  - FFmpeg libraries: ~50MB
  - Video codec libraries (x264, x265, etc.): ~60MB
  - VAAPI drivers and dependencies: ~50MB
  - Other codecs and filters: ~150MB
- **Python dependencies**: ~37MB
- **Application code**: ~5MB

The bulk of the size comes from FFmpeg's dependencies, especially:
- **LLVM** (127MB) - Required for OpenCL GPU acceleration
- **Mesa** (42MB) - Graphics drivers for GPU rendering
- **Codec libraries** - Support for various video formats

### Could We Go Smaller?

Yes, but with trade-offs:

1. **Minimal FFmpeg build** (~200-300MB total)
   - Build FFmpeg from source with only h264_vaapi/h264_nvenc
   - Skip OpenCL, extra codecs, filters
   - Much more complex Dockerfile
   - Longer build times

2. **Alpine Linux base** (~150-250MB total)
   - Use Alpine instead of Debian
   - Static FFmpeg binary
   - Compatibility issues with some Python packages

3. **Current approach** (~637MB total) **[RECOMMENDED]**
   - Best balance of size vs. simplicity
   - Full codec support for future needs
   - Easy to maintain and update
   - Proven compatibility

## Recommendation

**Use Debian FFmpeg** (proposed optimization) because:

1. **Size matters for Docker**: 200MB-1.3GB savings is significant
2. **Simplicity**: Easier to maintain and understand
3. **Stability**: Debian testing ensures compatibility
4. **Security**: Automatic updates through base image
5. **Feature complete**: Has all encoders we need
6. **Unified approach**: Could use single Dockerfile for both GPU types

The FFmpeg version difference (7.0 vs 7.1.2) is negligible for this use case. The features we need (h264_vaapi, h264_nvenc) are stable and work identically in both versions.

## Migration Path

1. Merge PR #216 (fixes broken functionality)
2. Create new PR with optimized Dockerfiles
3. Test with real hardware (Intel VAAPI and NVIDIA)
4. Update documentation with new build instructions
5. Publish optimized images to Docker Hub

## FFmpeg Version Options

### Current Approach (Recommended)
Uses Debian Trixie (testing) which provides **FFmpeg 7.1.2** - this is the latest stable 7.x release.

### Getting FFmpeg 8.0+
If you need the absolute latest FFmpeg (8.0+), use **Dockerfile.gpu-latest** which pulls from Debian Unstable (sid).

Trade-offs:
- **7.1.2 (Trixie)**: Stable, tested, recommended for production
- **8.0+ (Sid)**: Bleeding edge, may have bugs, good for testing new features

For tesla_dashcam, **7.1.2 is recommended** as it has all the features we need and is more stable.

## New Dockerfile Structure

Four options provided:

1. **Dockerfile.vaapi** - VAAPI-specific, FFmpeg 7.1.2 (637MB)
2. **Dockerfile.nvidia** - NVIDIA-specific, FFmpeg 7.1.2 (~480MB)
3. **Dockerfile.gpu** - Unified for both GPU types, FFmpeg 7.1.2 (637MB) **[RECOMMENDED]**
4. **Dockerfile.gpu-latest** - Unified with FFmpeg 8.0+ from Debian sid (~650MB)

All sizes assume proper .dockerignore to exclude .git and unnecessary files.

Recommendation: Use Dockerfile.gpu as the default, as it supports both GPU types with minimal overhead and uses stable FFmpeg 7.1.2.
