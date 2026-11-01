// Compile-only x64 ABI checks against the Windows SDK; no host queries.
#include <windows.h>
#include <cstddef>

static_assert(sizeof(void*) == 8);
static_assert(sizeof(DWORD) == 4);
static_assert(sizeof(LUID) == 8);
static_assert(offsetof(LUID, LowPart) == 0);
static_assert(offsetof(LUID, HighPart) == 4);
static_assert(sizeof(SID_IDENTIFIER_AUTHORITY) == 6);
static_assert(offsetof(SID, SubAuthority) == 8);
static_assert(SECURITY_MAX_SID_SIZE == 68);
static_assert(sizeof(SID_AND_ATTRIBUTES) == 16);
static_assert(offsetof(SID_AND_ATTRIBUTES, Sid) == 0);
static_assert(offsetof(SID_AND_ATTRIBUTES, Attributes) == 8);
static_assert(sizeof(TOKEN_USER) == 16);
static_assert(offsetof(TOKEN_USER, User) == 0);
static_assert(sizeof(TOKEN_MANDATORY_LABEL) == 16);
static_assert(offsetof(TOKEN_MANDATORY_LABEL, Label) == 0);
static_assert(sizeof(TOKEN_OWNER) == 8);
static_assert(offsetof(TOKEN_OWNER, Owner) == 0);
static_assert(sizeof(TOKEN_PRIMARY_GROUP) == 8);
static_assert(offsetof(TOKEN_PRIMARY_GROUP, PrimaryGroup) == 0);
static_assert(offsetof(TOKEN_GROUPS, GroupCount) == 0);
static_assert(offsetof(TOKEN_GROUPS, Groups) == 8);
static_assert(sizeof(LUID_AND_ATTRIBUTES) == 12);
static_assert(offsetof(LUID_AND_ATTRIBUTES, Luid) == 0);
static_assert(offsetof(LUID_AND_ATTRIBUTES, Attributes) == 8);
static_assert(offsetof(TOKEN_PRIVILEGES, PrivilegeCount) == 0);
static_assert(offsetof(TOKEN_PRIVILEGES, Privileges) == 4);
static_assert(sizeof(TOKEN_STATISTICS) == 56);
static_assert(offsetof(TOKEN_STATISTICS, TokenId) == 0);
static_assert(offsetof(TOKEN_STATISTICS, AuthenticationId) == 8);
static_assert(offsetof(TOKEN_STATISTICS, ExpirationTime) == 16);
static_assert(offsetof(TOKEN_STATISTICS, TokenType) == 24);
static_assert(offsetof(TOKEN_STATISTICS, ImpersonationLevel) == 28);
static_assert(offsetof(TOKEN_STATISTICS, DynamicCharged) == 32);
static_assert(offsetof(TOKEN_STATISTICS, DynamicAvailable) == 36);
static_assert(offsetof(TOKEN_STATISTICS, GroupCount) == 40);
static_assert(offsetof(TOKEN_STATISTICS, PrivilegeCount) == 44);
static_assert(offsetof(TOKEN_STATISTICS, ModifiedId) == 48);
