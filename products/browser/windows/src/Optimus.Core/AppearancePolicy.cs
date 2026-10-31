namespace Optimus.Core;
public enum ThemePreference { Dark=0, Light=1, System=2 }
public enum AppearancePalette { Dark, Light, HighContrast, SystemHighContrast }
public sealed record AppearanceState(AppearancePalette Palette,double TextScale,bool EasyMode);
public static class AppearancePolicy
{
 public static AppearanceState Resolve(BrowserSettings settings,bool systemDark,bool systemHighContrast)
 {
  ArgumentNullException.ThrowIfNull(settings);
  if(!Enum.IsDefined(settings.Theme)||!double.IsFinite(settings.TextScale)||settings.TextScale<1||settings.TextScale>2)throw new ArgumentException("Apariencia inválida",nameof(settings));
  var palette=systemHighContrast?AppearancePalette.SystemHighContrast:settings.HighContrast?AppearancePalette.HighContrast:settings.Theme==ThemePreference.Dark||settings.Theme==ThemePreference.System&&systemDark?AppearancePalette.Dark:AppearancePalette.Light;
  return new(palette,settings.EasyMode?Math.Max(1.25,settings.TextScale):settings.TextScale,settings.EasyMode);
 }
}
