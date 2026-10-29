namespace Optimus.Core;
public record OfficialSiteEntry(string ExactHost,Uri Reference,DateOnly ReviewedOn);
/// <summary>Operator-supplied exact entries only. No live verification or inferred subdomain trust.</summary>
public sealed class OfficialSiteRegistry(IEnumerable<OfficialSiteEntry> entries)
{
 private readonly OfficialSiteEntry[] registry=entries.ToArray();
 public string Describe(Uri site,DateOnly today)
 {
  if(!NavigationPolicy.IsAllowed(site))return "Candidato sin verificar";
  var entry=registry.FirstOrDefault(e=>string.Equals(e.ExactHost,site.IdnHost,StringComparison.OrdinalIgnoreCase));
  if(entry==null)return "Candidato sin verificar";
  var age=today.DayNumber-entry.ReviewedOn.DayNumber;
  if(age<0||age>30)return "Oficialidad pendiente de revisión · "+entry.ExactHost;
  return $"Oficial · {entry.ExactHost} · fuente {entry.Reference.GetLeftPart(UriPartial.Authority)} · revisión {entry.ReviewedOn:yyyy-MM-dd}";
 }
}
