#include "hack.h"
#include "nle.h"
int prepare_identify(nle_ctx_t* ctx) {
 struct nh_ctx* saved=nh_cur; nh_cur=(struct nh_ctx*)ctx->nh;
 struct obj* wand=mksobj(WAN_WISHING,TRUE,FALSE);
 wand->known=0; wand->dknown=1; objects[WAN_WISHING].oc_name_known=0;
 wand=addinv(wand); int target=(unsigned char)wand->invlet;
 struct obj* scroll=mksobj(SCR_IDENTIFY,TRUE,FALSE);
 scroll->blessed=0; scroll->cursed=1; scroll->bknown=1;
 scroll=addinv(scroll); int letter=(unsigned char)scroll->invlet;
 nh_cur=saved; return letter | (target<<8);
}
int check_identify(nle_ctx_t* ctx) {
 struct nh_ctx* saved=nh_cur;nh_cur=(struct nh_ctx*)ctx->nh; int ok=0;
 for(struct obj* o=invent;o;o=o->nobj)if(o->otyp==WAN_WISHING) ok=o->known && o->bknown && objects[o->otyp].oc_name_known;
 nh_cur=saved;return ok;
}
