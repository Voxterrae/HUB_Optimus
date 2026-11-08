# Proposal only: the defaults cannot be pulled. Supply separately reviewed .NET
# 10 SDK/runtime digest references only after image-build authorization.
# Build context: products/browser/search (not the repository or remote directory).
ARG DOTNET_SDK_IMAGE=registry.invalid/review-required-dotnet-sdk@sha256:0000000000000000000000000000000000000000000000000000000000000000
ARG DOTNET_RUNTIME_IMAGE=registry.invalid/review-required-dotnet-aspnet@sha256:0000000000000000000000000000000000000000000000000000000000000000
FROM ${DOTNET_SDK_IMAGE} AS build
WORKDIR /source
COPY global.json ./
COPY remote/src/Optimus.Search.Remote/Optimus.Search.Remote.csproj remote/src/Optimus.Search.Remote/
COPY src/Optimus.Search/LocalSearchIndex.cs src/Optimus.Search/SearchModels.cs src/Optimus.Search/
COPY catalog/public-pilot-v0.1.json catalog/public-pilot-v0.1.provenance.json catalog/
COPY remote/src/Optimus.Search.Remote/*.cs remote/src/Optimus.Search.Remote/
RUN test "$(dotnet --version)" = "10.0.403"
RUN dotnet restore remote/src/Optimus.Search.Remote/Optimus.Search.Remote.csproj
RUN dotnet publish remote/src/Optimus.Search.Remote/Optimus.Search.Remote.csproj --no-restore --configuration Release --output /out /p:UseAppHost=false

FROM ${DOTNET_RUNTIME_IMAGE} AS runtime
WORKDIR /app
COPY --from=build /out/ ./
USER 1654:1654
EXPOSE 8080
ENTRYPOINT ["dotnet", "Optimus.Search.Remote.dll"]
