using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class HeartHUD : MonoBehaviour
{
    [Header("BPM Display")]
    public TMP_Text bpmText;
    public TMP_Text etatText;
    public Image bpmBar;

    [Header("Alerte")]
    public GameObject alertePanel;
    public TMP_Text alerteText;

    [Header("Exercice")]
    public GameObject exercicePanel;
    public TMP_Text exerciceText;

    [Header("Couleurs")]
    public Color couleurNormal = Color.green;
    public Color couleurEleve = Color.yellow;
    public Color couleurDanger = Color.red;

    void Start()
    {
        if (alertePanel) alertePanel.SetActive(false);
        if (exercicePanel) exercicePanel.SetActive(false);
    }

    void Update()
    {
        MettreAJourBPM();
        MettreAJourAlerte();
    }

    void MettreAJourBPM()
    {
        int bpm = PythonConnector.BPM;
        string label = PythonConnector.Label;

        // Texte BPM
        if (bpmText)
            bpmText.text = bpm > 0 ? $"BPM: {bpm}" : "BPM: --";

        // Etat
        if (etatText)
            etatText.text = label;

        // Couleur
        Color couleur = couleurNormal;
        switch (PythonConnector.ActionJeu)
        {
            case "ralentir_jeu":
            case "pause_respiration":
                couleur = couleurEleve;
                break;
            case "mode_securise":
                couleur = couleurDanger;
                break;
        }

        if (bpmText) bpmText.color = couleur;
        if (etatText) etatText.color = couleur;

        // Barre BPM (0-200 BPM)
        if (bpmBar)
            bpmBar.fillAmount = Mathf.Clamp01(bpm / 200f);
    }

    void MettreAJourAlerte()
    {
        bool alerte = PythonConnector.Alerte;

        if (alertePanel)
            alertePanel.SetActive(alerte);

        if (alerte && alerteText)
            alerteText.text = PythonConnector.Message;

        if (exercicePanel)
            exercicePanel.SetActive(alerte);

        if (alerte && exerciceText)
            exerciceText.text = GetExercice();
    }

    string GetExercice()
    {
        switch (PythonConnector.ActionJeu)
        {
            case "ralentir_jeu":
                return "Inspire 4s... Expire 4s...";
            case "pause_respiration":
                return "Inspire 4s... Tiens 7s... Expire 8s...";
            case "mode_securise":
                return "STOP - Repose-toi maintenant !";
            default:
                return "Respire doucement...";
        }
    }
}