using UnityEngine;
using System.Collections.Generic;
using UnityEngine.AddressableAssets;

public class CharacterInputController : MonoBehaviour
{
    static int s_DeadHash = Animator.StringToHash("Dead");
    static int s_RunStartHash = Animator.StringToHash("runStart");
    static int s_MovingHash = Animator.StringToHash("Moving");
    static int s_JumpingHash = Animator.StringToHash("Jumping");
    static int s_JumpingSpeedHash = Animator.StringToHash("JumpSpeed");
    static int s_SlidingHash = Animator.StringToHash("Sliding");

    public TrackManager trackManager;
    public Character character;
    public CharacterCollider characterCollider;
    public GameObject blobShadow;
    public float laneChangeSpeed = 1.0f;
    public int maxLife = 3;
    public Consumable inventory;

    public int coins { get { return m_Coins; } set { m_Coins = value; } }
    public int premium { get { return m_Premium; } set { m_Premium = value; } }
    public int currentLife { get { return m_CurrentLife; } set { m_CurrentLife = value; } }
    public List<Consumable> consumables { get { return m_ActiveConsumables; } }
    public bool isJumping { get { return m_Jumping; } }
    public bool isSliding { get { return m_Sliding; } }

    [Header("Controls")]
    public float jumpLength = 2.0f;
    public float jumpHeight = 1.2f;
    public float slideLength = 2.0f;

    [Header("Sounds")]
    public AudioClip slideSound;
    public AudioClip powerUpUseSound;
    public AudioSource powerupSource;

    [HideInInspector] public int currentTutorialLevel;
    [HideInInspector] public bool tutorialWaitingForValidation;

    protected int m_Coins;
    protected int m_Premium;
    protected int m_CurrentLife;
    protected List<Consumable> m_ActiveConsumables = new List<Consumable>();
    protected int m_ObstacleLayer;
    protected bool m_IsInvincible;
    protected bool m_IsRunning;
    protected float m_JumpStart;
    protected bool m_Jumping;
    protected bool m_Sliding;
    protected float m_SlideStart;
    protected AudioSource m_Audio;
    protected int m_CurrentLane = k_StartingLane;
    protected Vector3 m_TargetPosition = Vector3.zero;
    protected readonly Vector3 k_StartingPosition = Vector3.forward * 2f;
    protected const int k_StartingLane = 1;
    protected const float k_GroundingSpeed = 80f;
    protected const float k_ShadowRaycastDistance = 100f;
    protected const float k_ShadowGroundOffset = 0.01f;
    protected const float k_TrackSpeedToJumpAnimSpeedRatio = 0.6f;
    protected const float k_TrackSpeedToSlideAnimSpeedRatio = 0.9f;

    protected void Awake()
    {
        m_Premium = 0;
        m_CurrentLife = 0;
        m_Sliding = false;
        m_SlideStart = 0.0f;
        m_IsRunning = false;
    }

    public void CheatInvincible(bool invincible) { m_IsInvincible = invincible; }
    public bool IsCheatInvincible() { return m_IsInvincible; }

    public void Init()
    {
        transform.position = k_StartingPosition;
        m_TargetPosition = Vector3.zero;
        m_CurrentLane = k_StartingLane;
        characterCollider.transform.localPosition = Vector3.zero;
        currentLife = maxLife;
        m_Audio = GetComponent<AudioSource>();
        m_ObstacleLayer = 1 << LayerMask.NameToLayer("Obstacle");
    }

    public void Begin()
    {
        m_IsRunning = false;
        character.animator.SetBool(s_DeadHash, false);
        characterCollider.Init();
        m_ActiveConsumables.Clear();
    }

    public void End() { CleanConsumable(); }

    public void CleanConsumable()
    {
        for (int i = 0; i < m_ActiveConsumables.Count; ++i)
        {
            m_ActiveConsumables[i].Ended(this);
            Addressables.ReleaseInstance(m_ActiveConsumables[i].gameObject);
        }
        m_ActiveConsumables.Clear();
    }

    public void StartRunning()
    {
        StartMoving();
        if (character.animator)
        {
            character.animator.Play(s_RunStartHash);
            character.animator.SetBool(s_MovingHash, true);
        }
    }

    public void StartMoving() { m_IsRunning = true; }

    public void StopMoving()
    {
        m_IsRunning = false;
        trackManager.StopMove();
        if (character.animator)
            character.animator.SetBool(s_MovingHash, false);
    }

    protected bool TutorialMoveCheck(int tutorialLevel)
    {
        tutorialWaitingForValidation = currentTutorialLevel != tutorialLevel;
        return (!TrackManager.instance.isTutorial || currentTutorialLevel >= tutorialLevel);
    }

    protected void Update()
    {
        // ═══════════════════════════════
        // HEART GUARDIAN — Logique ECG
        // ═══════════════════════════════
        string action = PythonConnector.ActionJeu;
        switch (action)
        {
            case "continuer_normal":
                m_IsInvincible = false;
                break;
            case "ralentir_jeu":
            case "pause_respiration":
            case "mode_securise":
                m_IsInvincible = true;
                break;
        }
        // ═══════════════════════════════

        // Seulement gauche/droite — pas de jump/slide
        if (Input.GetKeyDown(KeyCode.LeftArrow) && TutorialMoveCheck(0))
            ChangeLane(-1);
        else if (Input.GetKeyDown(KeyCode.RightArrow) && TutorialMoveCheck(0))
            ChangeLane(1);

        Vector3 verticalTargetPosition = m_TargetPosition;

        if (m_Sliding)
        {
            float correctSlideLength = slideLength * (1.0f + trackManager.speedRatio);
            float ratio = (trackManager.worldDistance - m_SlideStart) / correctSlideLength;
            if (ratio >= 1.0f) StopSliding();
        }

        if (m_Jumping)
        {
            if (trackManager.isMoving)
            {
                float correctJumpLength = jumpLength * (1.0f + trackManager.speedRatio);
                float ratio = (trackManager.worldDistance - m_JumpStart) / correctJumpLength;
                if (ratio >= 1.0f)
                {
                    m_Jumping = false;
                    character.animator.SetBool(s_JumpingHash, false);
                }
                else
                    verticalTargetPosition.y = Mathf.Sin(ratio * Mathf.PI) * jumpHeight;
            }
            else if (!AudioListener.pause)
            {
                verticalTargetPosition.y = Mathf.MoveTowards(
                    verticalTargetPosition.y, 0, k_GroundingSpeed * Time.deltaTime);
                if (Mathf.Approximately(verticalTargetPosition.y, 0f))
                {
                    character.animator.SetBool(s_JumpingHash, false);
                    m_Jumping = false;
                }
            }
        }

        characterCollider.transform.localPosition = Vector3.MoveTowards(
            characterCollider.transform.localPosition,
            verticalTargetPosition,
            laneChangeSpeed * Time.deltaTime
        );

        RaycastHit hit;
        if (Physics.Raycast(characterCollider.transform.position + Vector3.up,
            Vector3.down, out hit, k_ShadowRaycastDistance, m_ObstacleLayer))
            blobShadow.transform.position = hit.point + Vector3.up * k_ShadowGroundOffset;
        else
        {
            Vector3 shadowPosition = characterCollider.transform.position;
            shadowPosition.y = k_ShadowGroundOffset;
            blobShadow.transform.position = shadowPosition;
        }
    }

    public void Jump()
    {
        if (!m_IsRunning) return;
        if (!m_Jumping)
        {
            if (m_Sliding) StopSliding();
            float correctJumpLength = jumpLength * (1.0f + trackManager.speedRatio);
            m_JumpStart = trackManager.worldDistance;
            float animSpeed = k_TrackSpeedToJumpAnimSpeedRatio *
                (trackManager.speed / correctJumpLength);
            character.animator.SetFloat(s_JumpingSpeedHash, animSpeed);
            character.animator.SetBool(s_JumpingHash, true);
            m_Audio.PlayOneShot(character.jumpSound);
            m_Jumping = true;
        }
    }

    public void StopJumping()
    {
        if (m_Jumping)
        {
            character.animator.SetBool(s_JumpingHash, false);
            m_Jumping = false;
        }
    }

    public void Slide()
    {
        if (!m_IsRunning) return;
        if (!m_Sliding)
        {
            if (m_Jumping) StopJumping();
            float correctSlideLength = slideLength * (1.0f + trackManager.speedRatio);
            m_SlideStart = trackManager.worldDistance;
            float animSpeed = k_TrackSpeedToJumpAnimSpeedRatio *
                (trackManager.speed / correctSlideLength);
            character.animator.SetFloat(s_JumpingSpeedHash, animSpeed);
            character.animator.SetBool(s_SlidingHash, true);
            m_Audio.PlayOneShot(slideSound);
            m_Sliding = true;
            characterCollider.Slide(true);
        }
    }

    public void StopSliding()
    {
        if (m_Sliding)
        {
            character.animator.SetBool(s_SlidingHash, false);
            m_Sliding = false;
            characterCollider.Slide(false);
        }
    }

    public void ChangeLane(int direction)
    {
        if (!m_IsRunning) return;
        int targetLane = m_CurrentLane + direction;
        if (targetLane < 0 || targetLane > 2) return;
        m_CurrentLane = targetLane;
        m_TargetPosition = new Vector3(
            (m_CurrentLane - 1) * trackManager.laneOffset, 0, 0);
    }

    public void UseInventory()
    {
        if (inventory != null && inventory.CanBeUsed(this))
        {
            UseConsumable(inventory);
            inventory = null;
        }
    }

    public void UseConsumable(Consumable c)
    {
        characterCollider.audio.PlayOneShot(powerUpUseSound);
        for (int i = 0; i < m_ActiveConsumables.Count; ++i)
        {
            if (m_ActiveConsumables[i].GetType() == c.GetType())
            {
                m_ActiveConsumables[i].ResetTime();
                Addressables.ReleaseInstance(c.gameObject);
                return;
            }
        }
        c.transform.SetParent(transform, false);
        c.gameObject.SetActive(false);
        m_ActiveConsumables.Add(c);
        StartCoroutine(c.Started(this));
    }
}