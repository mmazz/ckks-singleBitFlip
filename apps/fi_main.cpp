


int main(int argc, char** argv) {
    CampaignArgs args = parse_arguments(argc, argv);
    BackendContext* ctx = setup_campaign(args);

    auto golden = run_iteration(ctx, args, std::nullopt);
    if (!baseline_ok(args, ctx, golden)) return 1;

    CampaignRegistry reg(args);
    if (reg.already_done()) return 0;
    CampaignLogger log(reg.campaign_id, args.results_dir + "/data");

    auto faults = args.isExhaustive ? exhaustive_faults(args, ctx)
                                    : random_faults(args, ctx);   // RNG sembrado
    for (const FaultSpec& f : faults) {
        auto res = run_iteration(ctx, args, f);
        log.log(f, compute_metrics(golden.values, res.values, args));
    }
    check_transient(ctx, args, golden);   // paso 4
    reg.register_end(log.summary());
}
