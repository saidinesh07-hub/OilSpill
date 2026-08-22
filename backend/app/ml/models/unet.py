"""
U-Net Segmentation Architecture for SAR Oil Spill Detection
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    """(Conv2D -> BatchNorm -> ReLU) * 2"""
    def __init__(self, in_channels: int, out_channels: int, dropout_p: float = 0.1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(p=dropout_p),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.conv(x)


class UNet(nn.Module):
    """
    Classic U-Net tailored for 5-class SAR pixel segmentation (256x256 tiles).
    Input: [B, C, H, W] where C=1 (VV) or C=2 (VV+VH)
    Output: [B, num_classes, H, W] logits
    """
    def __init__(self, in_channels: int = 1, num_classes: int = 5, base_features: int = 32):
        super().__init__()
        f = base_features

        # Encoder
        self.inc = DoubleConv(in_channels, f)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(f, f * 2))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(f * 2, f * 4))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(f * 4, f * 8))
        self.down4 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(f * 8, f * 16))

        # Decoder with Skip Connections
        self.up1 = nn.ConvTranspose2d(f * 16, f * 8, kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv(f * 16, f * 8)

        self.up2 = nn.ConvTranspose2d(f * 8, f * 4, kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv(f * 8, f * 4)

        self.up3 = nn.ConvTranspose2d(f * 4, f * 2, kernel_size=2, stride=2)
        self.conv_up3 = DoubleConv(f * 4, f * 2)

        self.up4 = nn.ConvTranspose2d(f * 2, f, kernel_size=2, stride=2)
        self.conv_up4 = DoubleConv(f * 2, f)

        # Output projection
        self.outc = nn.Conv2d(f, num_classes, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        x = self.up1(x5)
        x = self.conv_up1(torch.cat([x, x4], dim=1))

        x = self.up2(x)
        x = self.conv_up2(torch.cat([x, x3], dim=1))

        x = self.up3(x)
        x = self.conv_up3(torch.cat([x, x2], dim=1))

        x = self.up4(x)
        x = self.conv_up4(torch.cat([x, x1], dim=1))

        logits = self.outc(x)
        return logits
