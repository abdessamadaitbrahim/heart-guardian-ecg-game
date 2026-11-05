using UnityEngine;
using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class PythonConnector : MonoBehaviour
{
    [Header("Connexion Python")]
    public string pythonIP = "127.0.0.1";
    public int pythonPort = 6000;

    // Données ECG globales
    public static int BPM = 0;
    public static string Label = "EnAttente";
    public static bool Alerte = false;
    public static string ActionJeu = "continuer_normal";
    public static float Confiance = 0f;
    public static string Message = "";

    private TcpClient client;
    private NetworkStream stream;
    private Thread receiveThread;
    private bool running = false;
    private string buffer = "";

    void Start()
    {
        ConnecterPython();
    }

    void ConnecterPython()
    {
        try
        {
            client = new TcpClient(pythonIP, pythonPort);
            stream = client.GetStream();
            running = true;

            receiveThread = new Thread(RecevoirDonnees);
            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log("✅ Connecté à Python !");
        }
        catch (Exception e)
        {
            Debug.LogWarning($"⚠️ Python non connecté : {e.Message}");
        }
    }

    void RecevoirDonnees()
    {
        byte[] bytes = new byte[4096];

        while (running)
        {
            try
            {
                int count = stream.Read(bytes, 0, bytes.Length);
                if (count == 0) break;

                buffer += Encoding.UTF8.GetString(bytes, 0, count);

                while (buffer.Contains("\n"))
                {
                    int idx = buffer.IndexOf("\n");
                    string line = buffer.Substring(0, idx).Trim();
                    buffer = buffer.Substring(idx + 1);

                    if (!string.IsNullOrEmpty(line))
                        TraiterJSON(line);
                }
            }
            catch { break; }
        }
    }

    void TraiterJSON(string json)
    {
        try
        {
            var data = JsonUtility.FromJson<ECGData>(json);
            if (data == null) return;

            BPM = data.bpm;
            Label = data.label;
            Alerte = data.alerte;
            ActionJeu = data.action_jeu;
            Confiance = data.confiance;
            Message = data.message;
        }
        catch { }
    }

    public void EnvoyerProfil(string nom, int age, string maladie)
    {
        try
        {
            string json = $"{{\"type\":\"profil\",\"nom\":\"{nom}\",\"age\":{age},\"maladie\":\"{maladie}\"}}\n";
            byte[] data = Encoding.UTF8.GetBytes(json);
            stream.Write(data, 0, data.Length);
            Debug.Log($"✅ Profil envoyé : {nom}");
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Erreur envoi profil : {e.Message}");
        }
    }

    void OnDestroy()
    {
        running = false;
        stream?.Close();
        client?.Close();
    }
}

[Serializable]
public class ECGData
{
    public int bpm;
    public string label;
    public bool alerte;
    public string action_jeu;
    public float confiance;
    public string message;
}