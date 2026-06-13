from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=256)
    legalConsentAccepted: bool = False


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class LoginResponse(BaseModel):
    token: str
    user: dict


class RegisterResponse(BaseModel):
    ok: bool = True
    requiresVerification: bool = True
    email: str
    message: str


class UserSessionItem(BaseModel):
    id: str
    userAgent: str = ""
    ipAddress: str = ""
    isActive: bool = True
    isCurrent: bool = False
    createdAt: Optional[str] = None
    lastSeenAt: Optional[str] = None


class TokenPlanPublic(BaseModel):
    id: str
    name: str
    tokens: int
    priceUsdCents: int
    displayPrice: str = ""
    cycleLabel: str = "month"
    paypalPlanId: str = ""
    description: str = ""
    extraTokenUsdPerToken: float = 0.012
    extraTokenDisplayPrice: str = ""
    isFree: bool = False
    freeGenerationsPerDay: int = 0


class Entitlements(BaseModel):
    """Computed token plan limits (balance and charges are server-side only)."""
    tokenBalance: int = 0
    tokensPerText: int = 10
    tokensPerImage: int = 20
    tokensPerGeneration: int = 30
    tokensPerRefine: int = 30
    tokenUsdReference: float = 0.012
    generationsUsedToday: int = 0
    freeGenerationsPerDay: int = 1
    freeGenerationsRemainingToday: int = 0
    canGenerateWithTokens: bool = False
    canGenerateFreeToday: bool = False
    hasActiveSubscription: bool = False
    canTopUpTokens: bool = False
    activePlanId: str = ""
    subscriptionActive: bool = False
    generationsLimitPerDay: Optional[int] = None
    refineAllowed: bool = False
    imageOptionsCount: int = 1
    ctaOptionsCount: int = 2
    reputationScore: int = 100
    reputationZone: str = "good"
    canGenerate: bool = True
    canGenerateImages: bool = True
    refundsAllowed: bool = True
    reputationBlockedUntil: Optional[str] = None


class TokenTopUpRequest(BaseModel):
    tokenCount: int = Field(ge=1, le=100000)


class GenerationCostQuoteResponse(BaseModel):
    templateId: str
    includeImage: bool
    templateWantsImage: bool = False
    imagesAllowed: bool = True
    textTokens: int
    imageTokens: int
    totalTokens: int
    tokenBalance: int
    canAfford: bool
    usesFreeSlot: bool = False
    canGenerate: bool = True
    reputationScore: int = 100
    reputationZone: str = "good"


class TokenRefundRequestCreate(BaseModel):
    jobId: str
    message: str = Field(default="", max_length=2000)


class TokenRefundRequestItem(BaseModel):
    id: int
    jobId: str
    tokensRequested: int
    failureKind: str = ""
    userMessage: str = ""
    status: str
    adminNote: str = ""
    createdAt: Optional[str] = None
    resolvedAt: Optional[str] = None


class AdminRefundResolveRequest(BaseModel):
    approve: bool
    adminNote: str = Field(default="", max_length=2000)


class AccountSettingsResponse(BaseModel):
    email: str
    displayName: str = ""
    avatarUrl: str = ""
    settings: dict = Field(default_factory=dict)
    entitlements: Entitlements = Field(default_factory=Entitlements)


class AccountSettingsUpdateRequest(BaseModel):
    displayName: Optional[str] = None
    avatarUrl: Optional[str] = None
    settings: Optional[dict] = None
    email: Optional[EmailStr] = None


class PasswordUpdateRequest(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=256)
    newPassword: str = Field(min_length=6, max_length=256)

class CompanyProfileSchema(BaseModel):
    companyName: str = ""
    niche: str = ""
    productDescription: str = ""
    logoUrl: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    senderEmail: str = ""
    senderName: str = ""
    senderVerified: bool = False

class TemplateItem(BaseModel):
    id: str
    name: str
    previewImageUrl: str
    objectCounts: dict = Field(default_factory=dict)
    theme: dict = Field(default_factory=dict)
    isModular: bool = False
    blockLayout: List[dict] = Field(default_factory=list)
    isBuiltin: bool = True
    userTemplateId: Optional[int] = None


class UserTemplateItem(BaseModel):
    id: int
    name: str
    baseTemplateId: str = "custom"
    isModular: bool = True
    blockLayout: List[dict] = Field(default_factory=list)
    theme: dict = Field(default_factory=dict)
    updatedAt: Optional[str] = None


class UserTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    baseTemplateId: str = "custom"
    isModular: bool = True
    blockLayout: List[dict] = Field(default_factory=list)
    theme: dict = Field(default_factory=dict)


class UserTemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    blockLayout: Optional[List[dict]] = None
    theme: Optional[dict] = None

class ImageOption(BaseModel):
    id: str
    url: str
    alt: str = ""

class TextOption(BaseModel):
    id: str
    html: str

class CtaOption(BaseModel):
    id: str
    label: str
    href: str

class GenerationResult(BaseModel):
    sessionId: str
    generationId: Optional[str] = None
    templateId: str
    imageOptions: List[ImageOption]
    textOptions: List[TextOption]
    ctaOptions: List[CtaOption]
    subject: Optional[str] = None
    colorScheme: Optional[str] = None
    language: Optional[str] = None
    isModular: bool = False
    blockLayout: List[dict] = Field(default_factory=list)

class GenerateRequest(BaseModel):
    companyId: Optional[str] = None
    subject: str
    imageWishes: str = ""
    ctaLink: str = ""
    colorScheme: Optional[str] = None
    templateId: str
    language: Optional[str] = None
    blockLayout: Optional[List[dict]] = None


class GenerateJobStarted(BaseModel):
    jobId: str
    sessionId: str


class GenerateJobListItem(BaseModel):
    """Summary row for GET /api/generate/jobs (no full generation payload)."""

    jobId: str
    sessionId: str
    status: str
    stepKey: str
    progressStep: int = 0
    totalSteps: int = 3
    startedAt: Optional[str] = None
    subject: str = ""
    templateId: str = ""
    error: Optional[str] = None
    estimatedSecondsRemaining: Optional[int] = None
    failureKind: Optional[str] = None
    tokensCharged: int = 0
    refundStatus: str = "none"
    canRequestRefund: bool = False


class RefineRequest(BaseModel):
    sessionId: Optional[str] = None
    generationId: Optional[str] = None
    imageFeedback: Optional[str] = None
    textFeedback: Optional[str] = None
    ctaFeedback: Optional[str] = None
    templateId: Optional[str] = None
    language: Optional[str] = None


class GeneratedEmailListItem(BaseModel):
    id: int
    title: str = ""
    subject: str = ""
    templateId: str = ""
    isFavorite: bool = False
    tags: List[str] = Field(default_factory=list)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    previewText: str = ""


class GeneratedEmailDetail(BaseModel):
    id: int
    title: str = ""
    subject: str = ""
    templateId: str = ""
    isFavorite: bool = False
    tags: List[str] = Field(default_factory=list)
    payload: dict
    htmlSnapshot: str = ""
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class GeneratedEmailUpdateRequest(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    isFavorite: Optional[bool] = None
    subject: Optional[str] = None
    templateId: Optional[str] = None
    payload: Optional[dict] = None
    htmlSnapshot: Optional[str] = None


class GeneratedEmailCreateRequest(BaseModel):
    title: str = ""
    subject: str = ""
    templateId: str = ""
    payload: dict = Field(default_factory=dict)
    htmlSnapshot: str = ""

class ExportRequest(BaseModel):
    session_id: str
    image_index: int = 0
    text_index: int = 0
    cta_index: int = 0
    blockLayout: Optional[List[dict]] = None


class BlockLayoutItem(BaseModel):
    name: str
    context: dict = Field(default_factory=dict)


class RenderPreviewRequest(BaseModel):
    blockLayout: List[BlockLayoutItem]
    subject: str = ""
    theme: dict = Field(default_factory=dict)
    bodyHtml: str = ""
    imageUrl: Optional[str] = None
    ctaLink: Optional[str] = None
    ctaLabel: Optional[str] = None
