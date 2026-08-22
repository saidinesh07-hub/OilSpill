"""
DeepLabV3+ Architecture for Multi-Scale SAR Oil Spill & Look-Alike Segmentation
Implements Atrous Spatial Pyramid Pooling (ASPP) with dilation rates (1, 6, 12, 18).
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class ASPPConv(nn.Sequential):
    def __init__(self, in_channels: int, out_channels: int, dilation: int):
        modules = [
            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=dilation,
                dilation=dilation,
                bias=False
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        ]
        super().__init__(*modules)


class ASPPPooling(nn.Sequential):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        size = x.shape[-2:]
        for mod in self:
            x = mod(x)
        return F.interpolate(x, size=size, mode='bilinear', align_corners=False)


class ASPP(nn.Module):
    def __init__(self, in_channels: int, out_channels: int = 256, atrous_rates=(6, 12, 18)):
        super().__init__()
        modules = []
        # 1x1 conv
        modules.append(
            nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            )
        )
        # Dilated convs for capturing multi-scale slick plumes
        for rate in atrous_rates:
            modules.append(ASPPConv(in_channels, out_channels, rate))
        # Global context pooling
        modules.append(ASPPPooling(in_channels, out_channels))

        self.convs = nn.ModuleList(modules)
        self.project = nn.Sequential(
            nn.Conv2d(len(modules) * out_channels, out_channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3)
        )

    def forward(self, x):
        res = [conv(x) for conv in self.convs]
        res = torch.cat(res, dim=1)
        return self.project(res)


class DeepLabV3Plus(nn.Module):
    """
    DeepLabV3+ model with lightweight convolutional backbone for student compute efficiency.
    """
    def __init__(self, in_channels: int = 1, num_classes: int = 5, aspp_out_channels: int = 256):
        super().__init__()
        
        # High-Resolution Low-Level Feature Extractor
        self.entry_conv = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        # Mid-level features
        self.block1 = nn.Sequential(
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            nn.Conv2d(64, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True)
        )
        
        # Deep Features for ASPP (downsampled total stride = 8/16)
        self.block2 = nn.Sequential(
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 512, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True)
        )

        # ASPP module
        self.aspp = ASPP(in_channels=512, out_channels=aspp_out_channels, atrous_rates=(6, 12, 18))

        # Low-level feature projection for decoder
        self.low_level_proj = nn.Sequential(
            nn.Conv2d(64, 48, kernel_size=1, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )

        # High-resolution decoder
        self.decoder = nn.Sequential(
            nn.Conv2d(aspp_out_channels + 48, 256, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Conv2d(256, 256, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, num_classes, kernel_size=1)
        )

    def forward(self, x):
        input_size = x.shape[-2:]

        # Extract features
        low_level = self.entry_conv(x)  # H/2, W/2
        mid = self.block1(low_level)    # H/4, W/4
        high = self.block2(mid)         # H/8, W/8

        # ASPP
        aspp_out = self.aspp(high)

        # Upsample ASPP output to match low-level features
        aspp_up = F.interpolate(aspp_out, size=low_level.shape[-2:], mode='bilinear', align_corners=False)
        low_proj = self.low_level_proj(low_level)

        # Concatenate and decode
        fused = torch.cat([aspp_up, low_proj], dim=1)
        logits_half = self.decoder(fused)

        # Upsample final logits to original image size
        logits = F.interpolate(logits_half, size=input_size, mode='bilinear', align_corners=False)
        return logits
