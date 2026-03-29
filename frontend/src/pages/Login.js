import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { Server, Loader2, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex items-center justify-center p-4" data-testid="login-page">
      <div className="w-full max-w-sm">
        <div className="bg-white border border-[#E5E5E5] shadow-sm">
          {/* Header */}
          <div className="bg-[#0A0A0A] px-6 py-5 flex items-center gap-3">
            <div className="w-10 h-10 bg-[#002FA7] flex items-center justify-center">
              <Server className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">MCP Hub</h1>
              <p className="text-xs text-[#888] font-mono">CONTROL ROOM</p>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="flex items-center gap-2 text-sm text-[#FF2A2A] bg-[#FF2A2A]/5 border border-[#FF2A2A]/20 px-3 py-2" data-testid="login-error">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Email</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@mcphub.local"
                className="rounded-none border-[#E5E5E5] font-mono text-sm focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]"
                required
                data-testid="login-email-input"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="rounded-none border-[#E5E5E5] font-mono text-sm focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]"
                required
                data-testid="login-password-input"
              />
            </div>
            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-[#002FA7] hover:bg-[#001B66] text-white font-mono text-xs uppercase tracking-wider rounded-none h-10"
              data-testid="login-submit-button"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {loading ? "Authenticating..." : "Sign In"}
            </Button>
          </form>
        </div>
        <p className="text-center text-[10px] text-[#999] font-mono mt-4 uppercase tracking-wider">
          MCP Protocol v1.0
        </p>
      </div>
    </div>
  );
}
