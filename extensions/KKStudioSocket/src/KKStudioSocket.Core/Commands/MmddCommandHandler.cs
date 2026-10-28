using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Microsoft.Scripting.Hosting;

namespace KKStudioSocket.Commands
{
    public class MmddCommandHandler : BaseCommandHandler
    {
        public MmddCommandHandler(Action<string> sendCallback) : base(sendCallback) { }

        public void Handle(string requestJson, string resource = "mmdd_mcp_bridge.py")
        {
            try
            {
                // Reuse VNGE's live IronPython engine; a separate engine cannot access its loaded game state.
                var console = AppDomain.CurrentDomain.GetAssemblies()
                    .FirstOrDefault(a => a.GetName().Name == "Unity.Console");
                var program = console == null ? null : console.GetType("Unity.Console.Program");
                var getter = program == null ? null : program.GetMethod("get_MainEngine",
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                var engine = getter == null ? null : getter.Invoke(null, null) as ScriptEngine;
                if (engine == null)
                    throw new InvalidOperationException("VNGE Unity.Console engine is unavailable");
                using (var stream = typeof(MmddCommandHandler).Assembly.GetManifestResourceStream("KKStudioSocket." + resource))
                using (var reader = new StreamReader(stream))
                {
                    var scope = engine.CreateScope();
                    scope.SetVariable("mmdd_request_json", requestJson);
                    scope.SetVariable("animation_send_response", new Action<string>(Send));
                    engine.CreateScriptSourceFromString(reader.ReadToEnd()).Execute(scope);
                    var response = scope.GetVariable<string>("mmdd_response_json");
                    if (response != null) Send(response);
                }
            }
            catch (Exception ex)
            {
                Send(JsonConvert.SerializeObject(new { type = "error", message = ex.GetBaseException().Message }));
            }
        }
    }
}
